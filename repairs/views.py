from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
    View,
)

from .forms import RepairForm
from .models import Repair, RepairStatusHistory
from .services import (
    compress_repair_photo,
    generate_job_card_number,
    process_repair_status_change,
)


class ShopFilterMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(self.model, 'shop'):
            qs = qs.select_related('shop')
        return qs.filter(shop=self.request.shop, is_active=True)

class RepairListView(LoginRequiredMixin, ShopFilterMixin, ListView):
    model = Repair
    template_name = 'repairs/repair_list.html'
    context_object_name = 'repairs'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('customer', 'assigned_to')
        
        # Search functionality
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(job_card_number__icontains=q) |
                Q(customer__name__icontains=q) |
                Q(customer_phone_snapshot__icontains=q) |
                Q(customer__mobile_number__icontains=q)
            )
            
        # Filters
        status_filter = self.request.GET.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
            
        priority_filter = self.request.GET.get('priority')
        if priority_filter:
            qs = qs.filter(priority=priority_filter)
            
        assigned_filter = self.request.GET.get('assigned_to')
        if assigned_filter:
            qs = qs.filter(assigned_to_id=assigned_filter)
            
        repair_type_filter = self.request.GET.get('repair_type')
        if repair_type_filter:
            qs = qs.filter(repair_type__icontains=repair_type_filter)
            
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass filter choices to template
        from accounts.models import CustomUser
        context['staff_list'] = CustomUser.objects.filter(shop=self.request.shop)
        context['status_choices'] = Repair.STATUS_CHOICES
        context['priority_choices'] = Repair.PRIORITY_CHOICES
        return context

class RepairDetailView(LoginRequiredMixin, ShopFilterMixin, DetailView):
    model = Repair
    template_name = 'repairs/repair_detail.html'
    context_object_name = 'repair'

    def get_queryset(self):
        return super().get_queryset().prefetch_related('status_history__changed_by')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch audit timeline (oldest first for timeline)
        context['timeline'] = self.object.status_history.all().order_by('changed_at')
        
        # Next status choices options based on current status transition rules
        current_status = self.object.status
        next_options = []
        if current_status == 'RECEIVED':
            next_options = [('UNDER_REPAIR', 'Under Repair'), ('CANCELLED', 'Cancelled')]
        elif current_status == 'UNDER_REPAIR':
            next_options = [('READY', 'Ready'), ('CANCELLED', 'Cancelled')]
        elif current_status == 'READY':
            next_options = [('DELIVERED', 'Delivered'), ('CANCELLED', 'Cancelled')]
            
        context['next_status_options'] = next_options
        return context

class RepairCreateView(LoginRequiredMixin, CreateView):
    model = Repair
    form_class = RepairForm
    template_name = 'repairs/repair_form.html'

    def dispatch(self, request, *args, **kwargs):
        from core.services.permissions import PlanPermissionService
        if not PlanPermissionService.check(request.shop, 'create_repair'):
            messages.error(request, "Your trial or subscription has expired. Please upgrade to unlock this feature.")
            return redirect('repairs:repair_list')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['shop'] = self.request.shop
        return kwargs

    def form_valid(self, form):
        form.instance.shop = self.request.shop
        form.instance.created_by = self.request.user
        form.instance.customer_phone_snapshot = form.instance.customer.mobile_number
        form.instance.job_card_number = generate_job_card_number(form.instance)
        
        # Compress the uploaded photo
        if form.instance.item_photo:
            compress_repair_photo(form.instance.item_photo)
            
        response = super().form_valid(form)
        
        # Log initial creation state
        RepairStatusHistory.objects.create(
            repair=self.object,
            from_status=None,
            to_status='RECEIVED',
            changed_by=self.request.user,
            notes="Job Card generated and registered."
        )
        
        messages.success(self.request, f"Repair Job Card {self.object.job_card_number} created successfully!")
        return response

    def get_success_url(self):
        return reverse_lazy('repairs:repair_detail', kwargs={'pk': self.object.pk})

class RepairUpdateView(LoginRequiredMixin, ShopFilterMixin, UpdateView):
    model = Repair
    form_class = RepairForm
    template_name = 'repairs/repair_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['shop'] = self.request.shop
        return kwargs

    def form_valid(self, form):
        old_repair = self.get_object()
        old_status = old_repair.status
        new_status = form.cleaned_data.get('status')
        
        # Snap customer phone if changed
        form.instance.customer_phone_snapshot = form.instance.customer.mobile_number
        
        # Compress image if uploaded
        if 'item_photo' in form.changed_data and form.instance.item_photo:
            compress_repair_photo(form.instance.item_photo)

        if old_status != new_status:
            # Enforce transition rule check
            try:
                process_repair_status_change(
                    repair=old_repair,
                    to_status=new_status,
                    user=self.request.user,
                    notes="Updated via edit form."
                )
            except Exception as e:
                form.add_error('status', str(e))
                return self.form_invalid(form)
        
        response = super().form_valid(form)
        messages.success(self.request, f"Job Card {self.object.job_card_number} updated.")
        return response

    def get_success_url(self):
        return reverse_lazy('repairs:repair_detail', kwargs={'pk': self.object.pk})

class RepairStatusUpdateView(LoginRequiredMixin, ShopFilterMixin, View):
    """POST-only handler for fast status updates from the details page."""
    def post(self, request, pk):
        repair = get_object_or_404(Repair, pk=pk, shop=request.shop)
        to_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        try:
            process_repair_status_change(
                repair=repair,
                to_status=to_status,
                user=request.user,
                notes=notes
            )
            messages.success(request, f"Status transitioned to {repair.get_status_display()} successfully.")
        except Exception as e:
            messages.error(request, f"Failed to update status: {e!s}")
            
        return redirect('repairs:repair_detail', pk=repair.pk)

class RepairDeleteView(LoginRequiredMixin, ShopFilterMixin, DeleteView):
    model = Repair
    success_url = reverse_lazy('repairs:repair_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save()
        messages.success(request, "Repair job card archived successfully.")
        return redirect(self.get_success_url())

class RepairPDFView(LoginRequiredMixin, ShopFilterMixin, DetailView):
    model = Repair
    template_name = 'repairs/repair_pdf.html'
    context_object_name = 'repair'
