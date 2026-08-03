# Aureate SaaS - Tenant Isolation

This document outlines how multi-tenant data isolation is implemented and verified.

## Isolation Mechanism

1. **Request Interception (`TenantMiddleware`)**:
   - `TenantMiddleware` extracts the tenant shop based on user session authentication (`request.user.shop`) and assigns it to `request.shop`.
   - Populates active subscription limits (`request.subscription_status`) and locks endpoints (`request.subscription_locked`) if expired.

2. **QuerySet Scoping (`ShopFilterMixin`)**:
   - All CRUD views utilize `ShopFilterMixin`.
   - Overrides `get_queryset()` to inject `qs.filter(shop=request.shop)`.
   - Utilizes `select_related('shop')` by default to avoid N+1 database queries.

3. **API and Data Integrity Guards**:
   - Create forms populate the `shop` field automatically from `request.shop` in `form_valid()`.
   - Detail views raise 404 (Not Found) if a user attempts to request an item ID belonging to a different tenant.

## Testing Tenant Isolation

Each app contains isolation test suites (e.g., `inventory/tests/test_tenant_isolation.py`) validating:
- A user logged into Shop A receives lists containing only Shop A objects.
- Attempting to inspect or edit details of Shop B's objects returns 404 errors.
