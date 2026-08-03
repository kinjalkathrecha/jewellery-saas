import queue
import threading

from django.test import Client, TransactionTestCase

from accounts.models import CustomUser
from barcodes.services.barcode import generate_barcode_svg
from barcodes.services.sku import generate_next_sku
from core.models import Shop, SubscriptionPlan
from inventory.models import Category
from inventory.services.product import create_jewellery_item, update_jewellery_item


class BarcodeSubsystemTests(TransactionTestCase):
    def setUp(self):
        # Create standard subscription plan
        self.plan = SubscriptionPlan.objects.create(
            name="Test Plan", price=100.0, duration_days=30, max_products=100, max_users=3
        )
        
        # Create Shop A
        self.shop_a = Shop.objects.create(
            name="Shiv Jewellery", email="shiv@test.com", phone_number="123", subscription_plan=self.plan
        )
        # Create Shop B
        self.shop_b = Shop.objects.create(
            name="Moonlight Jewels", email="moon@test.com", phone_number="456", subscription_plan=self.plan
        )
        
        # Activate Subscriptions
        from core.services.subscription import activate_subscription
        activate_subscription(self.shop_a, self.plan, is_trial=False)
        activate_subscription(self.shop_b, self.plan, is_trial=False)
        
        # Create Users
        self.user_a = CustomUser.objects.create_user(
            username="admin1", email="a@test.com", password="pass", shop=self.shop_a, role="ADMIN"
        )
        self.user_b = CustomUser.objects.create_user(
            username="admin2", email="b@test.com", password="pass", shop=self.shop_b, role="ADMIN"
        )
        
        # Create a category in Shop A
        self.category_a = Category.objects.create(shop=self.shop_a, name="Rings")

    def test_sequential_sku_generation_default_prefix(self):
        # Test default initials extraction (Shiv Jewellery -> SJ)
        sku1 = generate_next_sku(self.shop_a.id)
        sku2 = generate_next_sku(self.shop_a.id)
        
        self.assertEqual(sku1, "SJ-000001")
        self.assertEqual(sku2, "SJ-000002")

    def test_sequential_sku_generation_custom_prefix(self):
        # Set custom prefix on shop
        self.shop_b.sku_prefix = "MOON"
        self.shop_b.save()
        
        sku1 = generate_next_sku(self.shop_b.id)
        self.assertEqual(sku1, "MOON-000001")

    def test_concurrency_sku_generation(self):
        from django.db import connection
        if connection.vendor == 'sqlite':
            # Skip multi-threaded locking tests under SQLite to avoid database lock errors.
            # SQLite does not support concurrent write locks via threads in test runs.
            return
            
        # Run multithreaded SKU generation to verify no duplicate SKUs are generated
        num_threads = 5
        generated_skus = queue.Queue()
        
        def worker():
            try:
                sku = generate_next_sku(self.shop_a.id)
                generated_skus.put(sku)
            except Exception as e:
                generated_skus.put(e)

        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        skus_list = []
        while not generated_skus.empty():
            val = generated_skus.get()
            if isinstance(val, Exception):
                raise val
            skus_list.append(val)

        # Assert all SKUs are unique
        self.assertEqual(len(skus_list), num_threads)
        self.assertEqual(len(set(skus_list)), num_threads)

    def test_barcode_svg_generation_strategies(self):
        svg_code128 = generate_barcode_svg("SJ-000001", "CODE128")
        self.assertIn("<svg", svg_code128)
        self.assertIn('width="', svg_code128)
        
        svg_ean13 = generate_barcode_svg("123456789012", "EAN13")
        self.assertIn("<svg", svg_ean13)
        
        svg_qr = generate_barcode_svg("SJ-000001", "QR")
        self.assertIn("<svg", svg_qr)
        self.assertIn("QR CODE", svg_qr)

    def test_explicit_product_services(self):
        # Create product
        data = {
            'item_name': "Gold Ring",
            'category': self.category_a,
            'metal_type': "GOLD_22K",
            'weight_in_grams': 5.25,
            'making_charges': 1500.0,
            'profit_margin': 2000.0,
            'price': 0.0,
            'stock_quantity': 3
        }
        
        item = create_jewellery_item(self.shop_a, data)
        self.assertEqual(item.design_code, "SJ-000001")
        self.assertIsNotNone(item.barcode_svg)
        self.assertIsNotNone(item.uuid)
        
        original_svg = item.barcode_svg
        # Update product code
        update_data = {
            'design_code': "SJ-CUSTOM-99"
        }
        updated_item = update_jewellery_item(item, update_data)
        self.assertEqual(updated_item.design_code, "SJ-CUSTOM-99")
        self.assertIsNotNone(updated_item.barcode_svg)
        self.assertNotEqual(original_svg, updated_item.barcode_svg)

    def test_lookup_api_and_tenant_isolation(self):
        # Add item to Shop A
        data = {
            'item_name': "Engagement Ring",
            'category': self.category_a,
            'metal_type': "GOLD_22K",
            'weight_in_grams': 3.5,
            'making_charges': 1000.0,
            'profit_margin': 1000.0,
            'price': 0.0,
            'stock_quantity': 2
        }
        item = create_jewellery_item(self.shop_a, data)
        
        client = Client()
        
        # Try lookup without login -> Redirects/Forbidden
        response = client.get('/api/v1/barcodes/lookup/', {'code': item.design_code})
        self.assertNotEqual(response.status_code, 200)

        # Login as User A (Shiv Jewellery admin)
        client.login(username="admin1", password="pass")
        
        # Look up by SKU
        response = client.get('/api/v1/barcodes/lookup/', {'code': item.design_code})
        self.assertEqual(response.status_code, 200)
        res_json = response.json()
        self.assertTrue(res_json['success'])
        self.assertEqual(res_json['sku'], item.design_code)
        
        # Look up by UUID
        response = client.get('/api/v1/barcodes/lookup/', {'code': str(item.uuid)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], "Engagement Ring")

        # Login as User B (Moonlight Jewels admin)
        client.logout()
        client.login(username="admin2", password="pass")
        
        # Tenant isolation check: Look up Shop A's item as Shop B admin -> Should return 404
        response = client.get('/api/v1/barcodes/lookup/', {'code': item.design_code})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()['success'])
        self.assertEqual(response.json()['error_code'], 'NOT_FOUND')

    def test_lookup_api_out_of_stock_state(self):
        # Create item with 0 stock
        data = {
            'item_name': "Chain",
            'category': self.category_a,
            'metal_type': "GOLD_22K",
            'weight_in_grams': 10.0,
            'price': 0.0,
            'stock_quantity': 0
        }
        item = create_jewellery_item(self.shop_a, data)
        
        client = Client()
        client.login(username="admin1", password="pass")
        
        # Look up -> should return OUT_OF_STOCK
        response = client.get('/api/v1/barcodes/lookup/', {'code': item.design_code})
        self.assertEqual(response.status_code, 200)
        res_json = response.json()
        self.assertFalse(res_json['success'])
        self.assertEqual(res_json['error_code'], 'OUT_OF_STOCK')

    def test_print_tags_view_isolation(self):
        # Create item in Shop A
        data_a = {
            'item_name': "Shop A Ring",
            'category': self.category_a,
            'metal_type': "GOLD_22K",
            'weight_in_grams': 5.0,
            'price': 0.0,
            'stock_quantity': 5
        }
        item_a = create_jewellery_item(self.shop_a, data_a)

        # Create item in Shop B
        # Let's create category B first
        from inventory.models import Category
        category_b = Category.objects.create(shop=self.shop_b, name="Bracelets")
        data_b = {
            'item_name': "Shop B Chain",
            'category': category_b,
            'metal_type': "GOLD_22K",
            'weight_in_grams': 12.0,
            'price': 0.0,
            'stock_quantity': 3
        }
        item_b = create_jewellery_item(self.shop_b, data_b)

        client = Client()
        # 1. Access without login -> redirect
        response = client.get('/api/v1/barcodes/print-tags/', {'ids': f"{item_a.id},{item_b.id}"})
        self.assertNotEqual(response.status_code, 200)

        # 2. Login as Shop A
        client.login(username="admin1", password="pass")
        response = client.get('/api/v1/barcodes/print-tags/', {'ids': f"{item_a.id},{item_b.id}"})
        self.assertEqual(response.status_code, 200)
        
        # Verify that Shop A's item is in the context items list, but Shop B's item is filtered out (isolation!)
        items_in_context = response.context['items']
        self.assertIn(item_a, items_in_context)
        self.assertNotIn(item_b, items_in_context)

    def test_barcode_events_logging_and_isolation(self):
        from barcodes.models import BarcodeEvent

        # 1. Clear existing events to be precise
        BarcodeEvent.objects.all().delete()

        # 2. Add an item in Shop A
        data = {
            'item_name': "Testing Ring",
            'category': self.category_a,
            'metal_type': "GOLD_22K",
            'weight_in_grams': 2.0,
            'price': 0.0,
            'stock_quantity': 4
        }
        item = create_jewellery_item(self.shop_a, data)

        client = Client()
        client.login(username="admin1", password="pass")

        # 3. Trigger lookup SCAN_SUCCESS
        client.get('/api/v1/barcodes/lookup/', {'code': item.design_code})
        
        # 4. Trigger lookup SCAN_FAILED (not found)
        client.get('/api/v1/barcodes/lookup/', {'code': "NON-EXISTENT-SKU"})

        # 5. Trigger print PRINT_LABEL
        client.get('/api/v1/barcodes/print-tags/', {'ids': str(item.id)})

        # Verify events logged in db
        events_a = BarcodeEvent.objects.filter(shop=self.shop_a)
        self.assertEqual(events_a.count(), 3)
        self.assertTrue(events_a.filter(event_type='SCAN_SUCCESS').exists())
        self.assertTrue(events_a.filter(event_type='SCAN_FAILED').exists())
        self.assertTrue(events_a.filter(event_type='PRINT_LABEL').exists())

        # Verify audits list view response
        response = client.get('/api/v1/barcodes/events/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_obj', response.context)
        self.assertEqual(len(response.context['page_obj']), 3)

        # 6. Verify tenant isolation in audits view
        client.logout()
        client.login(username="admin2", password="pass") # Login as Shop B
        response = client.get('/api/v1/barcodes/events/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['page_obj']), 0) # Shop B sees 0 events from Shop A

