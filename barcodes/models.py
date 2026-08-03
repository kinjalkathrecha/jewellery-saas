from django.db import models


class LabelTemplate(models.Model):
    shop = models.ForeignKey('core.Shop', on_delete=models.CASCADE, related_name='label_templates', null=True, blank=True, help_text="Null means global preset template.")
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    width_mm = models.IntegerField(default=50)
    height_mm = models.IntegerField(default=25)
    custom_css = models.TextField(blank=True, null=True, help_text="CSS overrides for printing layout alignment")
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['name', '-version']
        constraints = [
            models.UniqueConstraint(fields=['shop', 'slug', 'version'], name='unique_template_version_per_shop')
        ]

    def __str__(self):
        scope = self.shop.name if self.shop else "Global"
        return f"{self.name} v{self.version} ({scope})"


class BarcodeEvent(models.Model):
    EVENT_TYPES = [
        ('SCAN_SUCCESS', 'Scan Success'),
        ('SCAN_FAILED', 'Scan Failed'),
        ('PRINT_LABEL', 'Print Label'),
        ('PRINT_BULK', 'Print Bulk Labels'),
        ('QR_SCAN', 'QR Mobile Scan'),
        ('BARCODE_GENERATED', 'Barcode Generated'),
    ]

    shop = models.ForeignKey('core.Shop', on_delete=models.CASCADE, related_name='barcode_events')
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    sku_snapshot = models.CharField(max_length=100, blank=True, null=True, help_text="SKU identifier at the moment of log execution")
    product = models.ForeignKey('inventory.JewelleryItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='barcode_events')
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='barcode_events')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Store dynamic standardized metadata: module (POS/inventory/repairs), device details, IP, success/failure reason, etc.
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event_type} - {self.sku_snapshot} by {self.user} at {self.created_at}"
