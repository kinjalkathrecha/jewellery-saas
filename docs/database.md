# Aureate SaaS - Database Schema

This document details the database schemas, constraints, and relationships for the core models in Aureate.

## Core Models & Relationships

### 1. Shop (`core.models.Shop`)
- Represents a tenant (jewelry shop).
- Has `UniqueConstraint` on `subdomain` / `email`.
- Keeps track of the active subscription pointer (`active_subscription`).

### 2. JewelleryItem (`inventory.models.JewelleryItem`)
- Belongs to a `Shop` (ForeignKey).
- Belongs to a `Category` (ForeignKey).
- Enforces strict unique constraints on `(shop, design_code)` to prevent SKU collisions.
- Pricing can be `FIXED` or dynamic based on weight multiplied by the active `MetalRate` for Gold/Silver.

### 3. Invoice & InvoiceItem (`billing.models`)
- `Invoice` captures billing data scoped to `Shop` and optionally linked to `Customer`.
- `InvoiceItem` references the purchased `JewelleryItem` and records rate audit snapshots.
- Subtotal and total amounts are updated dynamically on invoice creation.

### 4. Repair (`repairs.models.Repair`)
- Represents a jewelry repair job card.
- Tracked via a unique `job_card_number` per shop.
- Uses `CheckConstraint` to enforce that `estimated_cost`, `actual_cost`, and `item_weight` are non-negative.
- Status transition logs are stored in `RepairStatusHistory`.
