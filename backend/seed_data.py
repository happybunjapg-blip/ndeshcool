"""Mock data. This is the ONLY file that will need to change (or be deleted)
when a real database is wired up -- AppState's shape stays identical.
"""
from datetime import timedelta
from models import Product, Batch, Customer, ProductCategory
from constants import TODAY, YESTERDAY


def seed_products():
    return [
        Product(
            name="10L Bottles", category=ProductCategory.BOTTLE_WATER,
            qty=15, threshold=5, selling_price=100, bottle_price=50, cost=60,
            batches=[
                Batch(10, 55, (TODAY - timedelta(days=20)).isoformat()),
                Batch(5, 65, (TODAY - timedelta(days=5)).isoformat()),
            ],
        ),
        Product(
            name="20L Bottles", category=ProductCategory.BOTTLE_WATER,
            qty=7, threshold=3, selling_price=180, bottle_price=80, cost=110,
            batches=[
                Batch(5, 105, (TODAY - timedelta(days=15)).isoformat()),
                Batch(2, 115, (TODAY - timedelta(days=3)).isoformat()),
            ],
        ),
        Product(
            name="5L Bottles", category=ProductCategory.BOTTLE_WATER,
            qty=40, threshold=10, selling_price=60, bottle_price=30, cost=35,
            batches=[
                Batch(30, 33, (TODAY - timedelta(days=30)).isoformat()),
                Batch(10, 38, (TODAY - timedelta(days=8)).isoformat()),
            ],
        ),
        Product(
            name="1L Sachets", category=ProductCategory.BOTTLE_WATER,
            qty=100, threshold=20, selling_price=10, bottle_price=5, cost=5,
            batches=[Batch(100, 4.5, (TODAY - timedelta(days=10)).isoformat())],
        ),
        Product(
            name="Bottle Caps", category=ProductCategory.ACCESSORY,
            qty=200, threshold=30, selling_price=2, bottle_price=0, cost=2,
            batches=[Batch(200, 2, (TODAY - timedelta(days=5)).isoformat())],
        ),
        Product(
            name="Water Pumps", category=ProductCategory.ACCESSORY,
            qty=3, threshold=2, selling_price=1500, bottle_price=0, cost=950,
            batches=[Batch(3, 950, (TODAY - timedelta(days=60)).isoformat())],
        ),
    ]


def seed_customers():
    return [
        Customer(id="C001", name="Grace Wanjiru", phone="0712 345 678",
                 is_credit=True, balance=850, notes="Prefers boda delivery."),
        Customer(id="C003", name="Fatuma Estates", phone="0722 909 090",
                 is_credit=True, balance=3200, notes="Corporate account, bulk deliveries."),
    ]


def seed_timeline():
    return [
        {"date": YESTERDAY.isoformat(), "time": "08:15", "event": "Restock — 20L Bottles",
         "type": "restock", "change": "+20", "stock_after": 25},
        {"date": YESTERDAY.isoformat(), "time": "09:02", "event": "Sale — 20L Bottles",
         "type": "sale", "change": "-2", "stock_after": 23},
        {"date": YESTERDAY.isoformat(), "time": "13:40", "event": "Sale — 10L Bottles",
         "type": "sale", "change": "-4", "stock_after": 14},
        {"date": YESTERDAY.isoformat(), "time": "17:55", "event": "Low Stock Warning — Water Pumps",
         "type": "warning", "change": "0", "stock_after": 3},
        {"date": TODAY.isoformat(), "time": "07:50", "event": "Restock — 5L Bottles",
         "type": "restock", "change": "+30", "stock_after": 40},
        {"date": TODAY.isoformat(), "time": "10:12", "event": "Sale — 1L Sachets",
         "type": "sale", "change": "-15", "stock_after": 85},
    ]


def seed_water_readings():
    return [
        {"date": (TODAY - timedelta(days=i)).isoformat(),
         "initial": 1000 + i * 50,
         "final": 1000 + (i + 1) * 50 - 10,
         "cleaning": 5 + i * 2,
         "sold_water": 40 + i * 5}
        for i in range(7, 0, -1)
    ]
