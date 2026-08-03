# Aureate SaaS - Subscriptions & Permissions

This document details subscription tiers, locks, grace periods, and permission enforcement.

## Subscription Tiers & Feature Limits
SaaS plan tiers enforce limits on:
- **Product Capacity**: E.g. Trial permits up to 50 items; Basic up to 1000 items.
- **Staff User Capacity**: Limit on the number of `CustomUser` roles registered per shop.
- **Monthly Invoicing Budget**: Limit on invoices compiled during a calendar month.

## Lockout Logic
- When a plan expires, a 3-day grace period is allowed.
- After the grace period, `shop.get_subscription_status()['is_locked']` evaluates to `True`.
- Middleware intercepts requests and locks access to write operations, displaying alert banners.

## Permissions Checking
- Checked via `PlanPermissionService.check(shop, action)`.
- Validates current counts against active limits before allowing records creation.
