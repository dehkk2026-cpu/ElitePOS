import json
import os

class POSStorage:
    def __init__(self):
        self.filename = "pos_data.json"
        self.data = {
            "products": [
                {"id": "1", "name": "Coffee (قهوة)", "price": 2.50, "category": "Drinks"},
                {"id": "2", "name": "Tea (شاي)", "price": 1.50, "category": "Drinks"},
                {"id": "3", "name": "Sandwich (شطيرة)", "price": 5.00, "category": "Food"},
                {"id": "4", "name": "Water (ماء)", "price": 1.00, "category": "Drinks"}
            ],
            "stats": {"total_orders": 0, "total_sales": 0.0},
            "printer": {"mac": "", "name": ""}
        }
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                    self.data.update(saved_data)
            except Exception as e:
                print(f"Error loading storage: {e}")
        else:
            self.save()

    def save(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving storage: {e}")

    def get_products(self):
        return self.data["products"]

    def add_product(self, product):
        self.data["products"].append(product)
        self.save()

    def get_stats(self):
        return self.data["stats"]

    def record_sale(self, total):
        self.data["stats"]["total_orders"] += 1
        self.data["stats"]["total_sales"] += total
        self.save()

    def clear_stats(self):
        self.data["stats"]["total_orders"] = 0
        self.data["stats"]["total_sales"] = 0.0
        self.save()

    def save_printer(self, mac, name):
        self.data["printer"] = {"mac": mac, "name": name}
        self.save()