import json

class StockUniverse:
    def __init__(self, filename="fo_universe.json"):
        # We now point directly to the tiny 3 KB file by default
        self.filename = filename

    def get_fo_stocks(self):
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                # Since we already filtered it, it loads instantly as a clean list!
                stocks = json.load(f)
            return stocks
        except FileNotFoundError:
            print(f"Error: {self.filename} not found. Please ensure it is in the directory.")
            return []