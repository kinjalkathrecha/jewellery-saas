# Aureate SaaS - Architecture Overview

This document describes the architectural layout, core patterns, and tech stack of Aureate SaaS.

## Tech Stack
- **Backend Framework**: Django 4.2 (Python 3.12)
- **Database**: PostgreSQL (Production/CI), SQLite (Testing fallback)
- **Task Runner/Linter**: Ruff
- **Test Engine**: Pytest with Pytest-Django
- **CI/CD**: GitHub Actions

## Directory Structure
- `/accounts`: Custom user models, user registration, role management (ADMIN vs STAFF).
- `/billing`: Invoicing, POS checkout system, billing cycle, PDF generation.
- `/core`: Global middleware, multi-tenancy context, subscription models, permission service.
- `/customers`: CRM module tracking customer details and customer lifetime value (total spent).
- `/inventory`: Dynamic jewelry pricing, metal rates tracking, item stocks, categories.
- `/repairs`: Repairs management system, statuses tracking, repair status logs.
- `/barcodes`: SVG tag layout printing and scanner audit events tracking.
- `/docs`: Project reference library.

## Architectural Patterns
1. **Multi-Tenancy**: Shared database, database-level logic isolation by filtering on `shop` context.
2. **Service Layer**: Core business processes (like creating items, activating plans, status transitions) are encapsulated in standalone service methods (`services.py` modules) rather than in views or models.
3. **Optimized Django Querysets**: Custom `ShopFilterMixin` uses `select_related('shop')` for optimized query execution, avoiding N+1 database queries.
