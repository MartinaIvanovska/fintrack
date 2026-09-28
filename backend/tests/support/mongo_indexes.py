

INDEXES = [
    ("users", [("email", 1)], {"unique": True}),
    ("users", [("username", 1)], {"unique": True}),
    ("transactions", [("user_id", 1), ("date", -1)], {}),
    ("transactions", [("user_id", 1), ("type", 1)], {}),
    ("transactions", [("user_id", 1), ("category_id", 1)], {}),
    ("transactions", [("description", "text"), ("merchant", "text")], {}),
    ("categories", [("user_id", 1), ("type", 1)], {}),
    ("budgets", [("user_id", 1), ("month_year", 1)], {}),
    ("budgets", [("user_id", 1), ("category_id", 1), ("month_year", 1)], {"unique": True}),
]


async def apply_indexes(db):
    for collection, keys, options in INDEXES:
        await db[collection].create_index(keys, **options)
