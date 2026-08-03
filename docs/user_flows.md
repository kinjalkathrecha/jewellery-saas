# Aureate SaaS - User Flows

This document details walk-through steps for critical user flows in Aureate.

## 1. Authentication & Login
1. User navigates to `/accounts/login/`.
2. Enters username and password credentials.
3. Middleware intercepts authentication, binds request context to matching shop, and checks subscription status.
4. User is redirected to `/` (dashboard). If expired, displays subscription upgrade prompt.

## 2. POS Billing to Invoice
1. Cashier scans barcode or searches jewelry catalog.
2. Selects active customer or chooses generic "Walking Customer".
3. Add item formset evaluates gold rate calculations dynamically.
4. Completes checkout: stock quantities are decremented, customer total spent is updated, and a PDF receipt is compiled.

## 3. Repair Job Card Lifecycle
1. Cashier registers a new repair order: inputs weight, category, photo, expected date, and estimated cost.
2. Job card number is generated automatically: `SHOP<id>-JOB-YYYYMMDD-<hash>`.
3. Repair timeline records state change history:
   `RECEIVED` $\rightarrow$ `UNDER_REPAIR` $\rightarrow$ `READY` $\rightarrow$ `DELIVERED`.
4. Delivers item and locks status as terminal state.
