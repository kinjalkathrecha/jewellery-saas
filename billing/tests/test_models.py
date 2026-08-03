import pytest

from tests.factories import InvoiceFactory


@pytest.mark.django_db
def test_invoice_totals():
    invoice = InvoiceFactory(subtotal=1000.00, tax_amount=30.00, total_amount=1030.00)
    assert invoice.subtotal == 1000.00
    assert invoice.tax_amount == 30.00
    assert invoice.total_amount == 1030.00
    assert str(invoice) == f"Invoice {invoice.invoice_number}"
