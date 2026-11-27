
import json
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Sunrise Hostel MCP Server")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


def load_json(filename: str) -> dict:
    """Load data from a JSON file."""
    file_path = DATA_DIR / filename

    with open(file_path, "r", encoding="utf-8-sig") as file:
        return json.load(file)


def find_guest(guest_id: str):
    """Find a guest using their guest ID."""
    data = load_json("guests.json")

    for guest in data["guests"]:
        if guest["guest_id"] == guest_id:
            return guest

    return None


def is_kitchen_open() -> bool:
    """Check whether the kitchen is currently operating."""
    kitchen = load_json("kitchen_hours.json")["kitchen"]
    now = datetime.now(ZoneInfo(kitchen["timezone"]))

    if now.strftime("%A") not in kitchen["operating_days"]:
        return False

    current_time = now.strftime("%H:%M")

    return (
        kitchen["opening_time"]
        <= current_time
        < kitchen["closing_time"]
    )


# --------------------------------------------------
# BOOKING SPECIALIST TOOLS
# --------------------------------------------------

@mcp.tool()
def get_guest_booking(guest_id: str) -> dict:
    """Retrieve booking details for a guest."""
    guest = find_guest(guest_id)

    if not guest:
        return {"error": "Guest not found"}

    return {
        "guest_id": guest["guest_id"],
        "name": guest["name"],
        "room_number": guest["room_number"],
        "booking": guest["booking"]
    }


@mcp.tool()
def request_checkout(guest_id: str) -> dict:
    """
    Request checkout approval for a guest.
    Does not perform checkout automatically.
    """
    guest = find_guest(guest_id)

    if not guest:
        return {"error": "Guest not found"}

    if guest["booking"]["status"] != "checked_in":
        return {
            "status": "rejected",
            "reason": "Only checked-in guests can request checkout."
        }

    return {
        "status": "pending_approval",
        "request_id": str(uuid.uuid4()),
        "action": "checkout",
        "guest_id": guest_id,
        "name": guest["name"],
        "room_number": guest["room_number"],
        "message": "Checkout requires guest approval before execution."
    }


# --------------------------------------------------
# KITCHEN SPECIALIST TOOLS
# --------------------------------------------------

@mcp.tool()
def get_menu() -> dict:
    """Retrieve menu items, stock availability and kitchen status."""
    menu = load_json("menu.json")

    return {
        "kitchen_open": is_kitchen_open(),
        "menu": menu["menu"]
    }


@mcp.tool()
def request_food_order(
    guest_id: str,
    item_id: str,
    quantity: int = 1
) -> dict:
    """
    Request approval for a food order.
    Does not place the order automatically.
    """
    guest = find_guest(guest_id)

    if not guest:
        return {"error": "Guest not found"}

    if guest["booking"]["status"] != "checked_in":
        return {
            "status": "rejected",
            "reason": "Only checked-in guests can order food."
        }

    if quantity < 1 or quantity > 10:
        return {
            "status": "rejected",
            "reason": "Quantity must be between 1 and 10."
        }

    menu = load_json("menu.json")["menu"]

    item = next(
        (entry for entry in menu if entry["item_id"] == item_id),
        None
    )

    if not item:
        return {
            "status": "rejected",
            "reason": "Menu item not found."
        }

    if not item["available"]:
        return {
            "status": "rejected",
            "reason": f"{item['name']} is currently out of stock."
        }

    if not is_kitchen_open():
        return {
            "status": "rejected",
            "reason": "The kitchen is currently closed."
        }

    return {
        "status": "pending_approval",
        "request_id": str(uuid.uuid4()),
        "action": "food_order",
        "guest_id": guest_id,
        "room_number": guest["room_number"],
        "item_id": item_id,
        "item_name": item["name"],
        "quantity": quantity,
        "total_price": item["price"] * quantity,
        "allergens": item["allergens"],
        "message": "Food order requires guest approval before execution."
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
