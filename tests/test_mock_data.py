
import json
import unittest
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load_json(filename):
    # utf-8-sig supports JSON files with or without a UTF-8 BOM
    with open(DATA_DIR / filename, "r", encoding="utf-8-sig") as file:
        return json.load(file)


class TestHostelMockData(unittest.TestCase):

    def test_guest_data(self):
        data = load_json("guests.json")
        guests = data["guests"]

        self.assertGreaterEqual(len(guests), 4)

        statuses = {guest["booking"]["status"] for guest in guests}
        self.assertIn("checked_in", statuses)
        self.assertIn("checked_out", statuses)
        self.assertIn("not_arrived", statuses)

    def test_menu_data(self):
        data = load_json("menu.json")
        menu = data["menu"]

        self.assertGreaterEqual(len(menu), 6)

        unavailable_items = [
            item for item in menu if not item["available"]
        ]
        peanut_items = [
            item for item in menu
            if "peanuts" in item["allergens"]
        ]

        self.assertGreaterEqual(len(unavailable_items), 1)
        self.assertGreaterEqual(len(peanut_items), 1)

    def test_kitchen_hours(self):
        data = load_json("kitchen_hours.json")
        kitchen = data["kitchen"]

        self.assertIn("opening_time", kitchen)
        self.assertIn("closing_time", kitchen)
        self.assertEqual(kitchen["timezone"], "Asia/Kolkata")


if __name__ == "__main__":
    unittest.main()
