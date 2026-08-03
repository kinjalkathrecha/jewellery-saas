import pytest

from inventory.services.product import create_jewellery_item, update_jewellery_item
from tests.factories import CategoryFactory, JewelleryItemFactory, ShopFactory


@pytest.mark.django_db
def test_create_jewellery_item_service():
    shop = ShopFactory()
    category = CategoryFactory(shop=shop)
    
    data = {
        'item_name': 'Gold Ring 22K',
        'category': category,
        'metal_type': 'FIXED',
        'weight_in_grams': 4.5,
        'making_charges': 300.00,
        'profit_margin': 200.00,
        'price': 25000.00,
        'stock_quantity': 5,
        'design_code': 'SKU-RG-100',
        'barcode_type': 'CODE128'
    }
    
    item = create_jewellery_item(shop, data)
    
    assert item.item_name == 'Gold Ring 22K'
    assert item.category == category
    assert item.price == 25000.00
    assert item.stock_quantity == 5
    assert item.design_code == 'SKU-RG-100'
    assert item.barcode_svg is not None

@pytest.mark.django_db
def test_update_jewellery_item_service():
    shop = ShopFactory()
    item = JewelleryItemFactory(shop=shop, design_code='OLD-SKU', barcode_type='CODE128')
    
    data = {
        'item_name': 'Updated Ring Name',
        'design_code': 'NEW-SKU'
    }
    
    updated_item = update_jewellery_item(item, data)
    
    assert updated_item.item_name == 'Updated Ring Name'
    assert updated_item.design_code == 'NEW-SKU'
    assert updated_item.barcode_svg is not None
