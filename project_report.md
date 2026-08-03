# Jewellery SaaS - Comprehensive Project Report

This report outlines the architecture, technology stack, data schema, key features, security mechanics, and recent enhancements of the **Jewellery Shop SaaS** platform.

---

## 1. Project Overview & Core Concept
**Jewellery SaaS** is a multi-tenant, cloud-based software-as-a-service application designed for retail jewelry stores. It streamlines business operations across multiple shops (tenants), managing inventory, dynamic metal pricing, repairs (job cards), point of sale (POS) billing, barcode/QR code label printing, and subscriber access control.

### Core Technology Stack
- **Backend Framework**: Django 4.2.30 (Python)
- **Database**: PostgreSQL (via `psycopg` connector)
- **Frontend**: Bootstrap 5, HTML5/Vanilla CSS, Boxicons, Chart.js for data visualization
- **Barcode Engine**: Code 128 / EAN-13 / QR Code SVG generator
- **Linter & Verification**: Pyrefly, Django Check Framework, Selenium & Pytest/unittest

---

## 2. Multi-Tenant Architecture & Subscriptions
The system enforces strict data isolation between shops using a shared-database, tenant-aware design model. 

### Middleware Isolation
- The `TenantMiddleware` detects the logged-in user's shop and injects `request.shop` into the incoming request.
- Subscription logic runs automatically to determine `request.subscription_active`, `request.subscription_locked`, and `request.subscription_message`.
- If a shop's subscription expires, the middleware locks write permissions while maintaining read-only dashboard access.

### Subscription Lifecycle Flow
```mermaid
state_cycle [Subscription States]
state_cycle: TRIAL (7 days default) --> ACTIVE (Fully Paid)
state_cycle: ACTIVE --> GRACE_PERIOD (Grace Days Warning)
state_cycle: GRACE_PERIOD --> EXPIRED (Feature Lockout)
state_cycle: EXPIRED --> ACTIVE (After Upgrade/Renewal)
```

---

## 3. Data Schema & Models
The project is modularized into nine distinct applications.

### Core Domain Models
1. **`accounts.CustomUser`**: Extends Django's `AbstractUser`. Stores the user's `role` (`ADMIN` or `STAFF`) and links them to a specific `Shop`.
2. **`core.Shop`**: Represents a single jewelry retailer tenant. Houses billing profiles, next SKU counts, trial endpoints, and subscription relations.
3. **`core.SubscriptionPlan` & `Subscription`**: Details limits on items (`max_products`), users (`max_users`), and invoices (`max_invoices_per_month`), tracking payment dates.
4. **`inventory.Category` & `JewelleryItem`**:
   - `JewelleryItem` stores weight, making charges, metal categories, design codes, UUIDs, and current stock.
   - Supports **Dynamic Pricing**: price calculates on-save using the active metal rate (`metal_cost = weight_in_grams * metal_rate_used`), unless set to `FIXED`.
5. **`inventory.MetalRate`**: Daily pricing metrics for `GOLD_24K`, `GOLD_22K`, `GOLD_18K`, and `SILVER`.
6. **`customers.Customer`**: Tracks customer mobile numbers, total lifetime sales, and demographic data.
7. **`repairs.Repair`**: Manages repairs/job cards. Tracks statuses (`RECEIVED` $\rightarrow$ `UNDER_REPAIR` $\rightarrow$ `READY` $\rightarrow$ `DELIVERED` $\rightarrow$ `CANCELLED`), estimated vs actual costs, assigned technicians, and expected delivery dates.
8. **`billing.Invoice` & `InvoiceItem`**: POS invoices recording snapshot rates, item dimensions, taxes, subtotals, and custom terms.
9. **`barcodes.LabelTemplate` & `BarcodeEvent`**: Presets for barcode prints and logs tracking scans/events.

---

## 4. Key Workflows

### Dynamic Metal Pricing
```
             +------------------------------+
             | Dynamic Price Calculation    |
             | (GOLD_24K / 22K / 18K / Ag)  |
             +--------------+---------------+
                            |
         Weight * Rate + Making Charges + Margin
                            |
                            v
             +------------------------------+
             | Saved as JewelleryItem.price |
             +------------------------------+
```

### Invoice POS Generation
1. Items are scanned via barcode or selected manually.
2. Rates are snapshotted to `InvoiceItem` to prevent historical billing edits if metal rates change.
3. Quantities deduct from `JewelleryItem.stock_quantity`.
4. Lifetime customer spend updates inside `Customer.total_spent`.

---

## 5. Security & Permission Control
Role-Based Access Control (RBAC) separates permissions:
- **`ADMIN` Role**: Accesses store settings (`dashboard:shop_settings`), staff registrations (`accounts:staff_list`), and subscription billing detail.
- **`STAFF` Role**: Limited to POS generation, customer registrations, repair status tracking, and inventory views.
- **Subscription Guardrails**: Invoices and products are guarded by check blocks. If a user exceeds plan limits (e.g. adding the 1001st product on a 1000-item plan), the action is blocked.

---

## 6. Recent Template Bug Fixes

We resolved several runtime and linting errors to stabilize the dashboard:

| File | Component | Issue | Action Taken |
| :--- | :--- | :--- | :--- |
| **`reports.html`** | Chart.js JS Block | Syntax error (`Unexpected token ')'`) crashed Chart.js execution because the `options` block was closed with `});` instead of `}`. | Properly closed the `options` block and resolved the Chart initialization. |
| **`reports.html`** | Script Data Parsing | Inline django variables (like `{{ sales_trend|safe }}`) triggered IDE parser syntax errors inside JS script tags. | Migrated variables to Django `<script type="application/json">` via `json_script` filters, then retrieved securely using `JSON.parse`. |
| **`home.html`** | Low Stock Card | Rendered `{{ low_stock_items.count }}` on a sliced QuerySet. This capped the displayed count at `5` and risked database-specific exceptions. | Computed `low_stock_count` on the unsliced QuerySet in `views.py` and passed it safely to the template context. |
| **`home.html`** | CSS / HTML Linter | Inline styles using template braces (e.g. `style="width: {{ prod_percent }}%"`) generated static syntax errors. | Migrated variables to `data-width` attributes, initializing widths dynamically on load using a clean `extra_js` helper. |
