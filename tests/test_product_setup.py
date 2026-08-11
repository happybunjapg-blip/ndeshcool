"""Regression tests for V1 Product Setup.

Covers:
  - Add Product
  - Edit Product
  - Archive Product
  - Sales loads active products only
  - Different businesses only see their own products
"""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import Product, ProductCategory
from backend.memory_repository import MemoryRepository
from backend.state import AppState


class ProductSetupTests(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryRepository()
        self.state = AppState(self.repo)
        self.repo.set_business_id("biz-1")

    def _make_product(self, name="Test Product", price=100.0, track=True, active=True):
        return Product(
            name=name,
            selling_price=price,
            track_inventory=track,
            active=active,
        )

    # ---------------------------------------------------------------
    # Add Product
    # ---------------------------------------------------------------
    def test_add_product(self):
        product = self._make_product("20L Bottles", 200.0)
        self.state.add_product(product)

        self.assertEqual(len(self.state.products), 1)
        self.assertEqual(self.state.products[0].name, "20L Bottles")
        self.assertEqual(self.state.products[0].selling_price, 200.0)
        self.assertTrue(self.state.products[0].active)
        self.assertTrue(self.state.products[0].track_inventory)
        self.assertEqual(self.state.products[0].business_id, "biz-1")
        self.assertTrue(self.state.products[0].id)

    def test_add_product_sets_timestamps(self):
        product = self._make_product("Bottle Caps", 5.0)
        self.state.add_product(product)

        self.assertTrue(product.created_at)
        self.assertTrue(product.updated_at)

    # ---------------------------------------------------------------
    # Edit Product
    # ---------------------------------------------------------------
    def test_edit_product(self):
        product = self._make_product("10L Bottles", 100.0)
        self.state.add_product(product)

        product.name = "10L Bottles (New)"
        product.selling_price = 120.0
        product.track_inventory = False
        self.state.update_product(product)

        updated = self.state.get_product_by_id(product.id)
        self.assertEqual(updated.name, "10L Bottles (New)")
        self.assertEqual(updated.selling_price, 120.0)
        self.assertFalse(updated.track_inventory)
        self.assertTrue(updated.updated_at)

    # ---------------------------------------------------------------
    # Archive / Activate Product
    # ---------------------------------------------------------------
    def test_archive_product(self):
        product = self._make_product("Water Pumps", 1500.0)
        self.state.add_product(product)

        self.state.set_product_active(product.id, False)

        archived = self.state.get_product_by_id(product.id)
        self.assertFalse(archived.active)

    def test_activate_product(self):
        product = self._make_product("Water Pumps", 1500.0, active=False)
        self.state.add_product(product)

        self.state.set_product_active(product.id, True)

        activated = self.state.get_product_by_id(product.id)
        self.assertTrue(activated.active)

    # ---------------------------------------------------------------
    # Sales loads active products only
    # ---------------------------------------------------------------
    def test_list_active_products_excludes_archived(self):
        active = self._make_product("Active Product", 100.0, active=True)
        archived = self._make_product("Archived Product", 200.0, active=False)
        self.state.add_product(active)
        self.state.add_product(archived)

        active_products = self.state.list_active_products()

        self.assertEqual(len(active_products), 1)
        self.assertEqual(active_products[0].name, "Active Product")

    def test_list_active_products_returns_all_when_all_active(self):
        p1 = self._make_product("Product A", 100.0)
        p2 = self._make_product("Product B", 200.0)
        self.state.add_product(p1)
        self.state.add_product(p2)

        active_products = self.state.list_active_products()

        self.assertEqual(len(active_products), 2)

    # ---------------------------------------------------------------
    # Different businesses only see their own products
    # ---------------------------------------------------------------
    def test_business_scoping(self):
        # Business 1 adds products
        self.repo.set_business_id("biz-1")
        p1 = self._make_product("Biz1 Product", 100.0)
        self.state.add_product(p1)

        # Business 2 adds products
        self.repo.set_business_id("biz-2")
        p2 = self._make_product("Biz2 Product", 200.0)
        self.state.add_product(p2)

        # Business 1 sees only its own
        self.repo.set_business_id("biz-1")
        self.state.refresh()
        biz1_products = self.state.list_active_products()
        self.assertEqual(len(biz1_products), 1)
        self.assertEqual(biz1_products[0].name, "Biz1 Product")

        # Business 2 sees only its own
        self.repo.set_business_id("biz-2")
        self.state.refresh()
        biz2_products = self.state.list_active_products()
        self.assertEqual(len(biz2_products), 1)
        self.assertEqual(biz2_products[0].name, "Biz2 Product")

    def test_archived_product_not_in_sales_list(self):
        """Archived products must not appear in the sales dropdown list."""
        active = self._make_product("Active Item", 50.0, active=True)
        archived = self._make_product("Archived Item", 75.0, active=False)
        self.state.add_product(active)
        self.state.add_product(archived)

        sales_products = self.state.list_active_products()
        names = [p.name for p in sales_products]

        self.assertIn("Active Item", names)
        self.assertNotIn("Archived Item", names)


if __name__ == "__main__":
    unittest.main()