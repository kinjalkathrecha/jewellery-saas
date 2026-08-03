# Aureate SaaS - Testing Guide

This document describes how to execute, verify, and write tests for Aureate.

## Running Tests
Run pytest in the workspace root:
```bash
pytest
```
Pytest automatically loads database configurations and scans for app-level tests inside `tests/` folders.

## Enforcing Code Coverage
Coverage targets are configured in `pytest.ini`:
```ini
addopts = --cov=. --cov-fail-under=80 --cov-report=xml --cov-report=term-missing
```
The test suite fails if total statement coverage drops below **80%**.

## Writing New Tests
1. **Modular Factories**: Import factories from the `tests.factories` module:
   ```python
   from tests.factories import ShopFactory, JewelleryItemFactory
   ```
2. **Database Scoping**: Mark test functions requiring database access with the Django DB decorator:
   ```python
   @pytest.mark.django_db
   def test_my_logic():
       # ...
   ```
3. **Query Budgets**: Assert database query count optimizations using `django_assert_num_queries`:
   ```python
   def test_queries(django_assert_num_queries):
       with django_assert_num_queries(5):
           # execute view logic
   ```
