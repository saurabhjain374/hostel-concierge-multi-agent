
import sys
from typing import Any

from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient


def create_specialist_toolsets(
    guest_id: str,
    tool_map: dict
):
    """
    Create separate, guest-scoped toolsets for Booking and Kitchen.

    Each specialist receives only its permitted tools.
    Guest identity is supplied by the application.
    """

    if not guest_id:
        raise ValueError("Guest ID is required.")

    # -------------------------------------------------
    # 1. Booking Specialist secure wrappers
    # -------------------------------------------------

    @tool
    async def get_my_booking() -> str:
        """Retrieve the authenticated guest's booking details."""

        result = await tool_map["get_guest_booking"].ainvoke({
            "guest_id": guest_id
        })

        return str(result)

    @tool
    async def request_my_checkout() -> str:
        """Request checkout approval for the authenticated guest."""

        result = await tool_map["request_checkout"].ainvoke({
            "guest_id": guest_id
        })

        return str(result)

    booking_tools = [
        get_my_booking,
        request_my_checkout,
    ]

    # -------------------------------------------------
    # 2. Kitchen Specialist secure wrappers
    # -------------------------------------------------

    @tool
    async def get_kitchen_menu() -> str:
        """Retrieve menu, prices, stock and kitchen status."""

        result = await tool_map["get_menu"].ainvoke({})

        return str(result)

    @tool
    async def request_my_food_order(
        item_id: str,
        quantity: int = 1
    ) -> str:
        """Request approval for a food order."""

        result = await tool_map["request_food_order"].ainvoke({
            "guest_id": guest_id,
            "item_id": item_id,
            "quantity": quantity,
        })

        return str(result)

    kitchen_tools = [
        get_kitchen_menu,
        request_my_food_order,
    ]

    return booking_tools, kitchen_tools


async def create_specialist_agents(guest_id: str):
    """
    Create Booking and Kitchen Specialist agents.

    Guest ID is supplied by the application.
    Each specialist receives only its permitted tools.
    """

    if not guest_id:
        raise ValueError("Guest ID is required.")

    # -------------------------------------------------
    # 1. Connect to MCP server
    # -------------------------------------------------

    server_config: dict[str, Any] = {
        "sunrise_hostel": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", "src.mcp_server.server"],
        }
    }

    client = MultiServerMCPClient(server_config)

    all_tools = await client.get_tools()

    print("\nDiscovered MCP tools:")
    for mcp_tool in all_tools:
        print(f"- {mcp_tool.name}")

    tool_map = {
        mcp_tool.name: mcp_tool
        for mcp_tool in all_tools
    }

    # -------------------------------------------------
    # 2. Create separate specialist toolsets
    # -------------------------------------------------

    required_tools = {
        "get_guest_booking",
        "request_checkout",
        "get_menu",
        "request_food_order",
    }

    missing_tools = required_tools - set(tool_map)

    if missing_tools:
        raise RuntimeError(
            f"Required MCP tools are missing: {sorted(missing_tools)}"
        )

    booking_tools, kitchen_tools = create_specialist_toolsets(
        guest_id,
        tool_map
    )

    print("\nBooking Specialist tools:")
    for specialist_tool in booking_tools:
        print(f"- {specialist_tool.name}")

    print("\nKitchen Specialist tools:")
    for specialist_tool in kitchen_tools:
        print(f"- {specialist_tool.name}")

    # -------------------------------------------------
    # 3. LLM configuration
    # -------------------------------------------------

    model = ChatOllama(
        model="llama3.2:3b",
        temperature=0
    )

    # -------------------------------------------------
    # 4. Booking Specialist
    # -------------------------------------------------

    booking_agent = create_react_agent(
        model=model,
        tools=booking_tools,
        prompt=(
            "You are the Booking Specialist for Sunrise Hostel.\n\n"

            "YOUR RESPONSIBILITIES:\n"
            "- Retrieve the authenticated guest's booking.\n"
            "- Explain booking dates and room details.\n"
            "- Handle checkout requests.\n\n"

            "STRICT RULES:\n"
            "- Always use tools to retrieve booking information.\n"
            "- Treat tool results as the only source of truth.\n"
            "- Never invent room types, prices or availability.\n"
            "- Never invent booking dates or policies.\n"
            "- Never access another guest's booking.\n"
            "- Never ask the guest for their guest ID or room number.\n"
            "- Checkout requests must use the checkout approval tool.\n"
            "- Never claim checkout is completed when approval is pending.\n"
            "- Clearly communicate rejected requests and their reasons.\n"
            "- If information is unavailable, say so honestly.\n"
        )
    )

    # -------------------------------------------------
    # 5. Kitchen Specialist
    # -------------------------------------------------

    kitchen_agent = create_react_agent(
        model=model,
        tools=kitchen_tools,
        prompt=(
            "You are the Kitchen Specialist for Sunrise Hostel.\n\n"

            "YOUR RESPONSIBILITIES:\n"
            "- Retrieve the menu and food prices.\n"
            "- Check food stock availability.\n"
            "- Report kitchen operating status.\n"
            "- Handle guest food-order requests.\n\n"

            "STRICT RULES:\n"
            "- Always use get_kitchen_menu for menu questions.\n"
            "- Treat tool results as the only source of truth.\n"
            "- Never invent menu items or prices.\n"
            "- All prices are in Indian Rupees (INR).\n"
            "- Never convert prices into another currency.\n"
            "- Never invent kitchen opening or closing times.\n"
            "- Report kitchen status as returned by the tool.\n"
            "- Never claim unavailable items are available.\n"
            "- Mention allergens returned by the tool.\n"
            "- Never invent ingredients or allergen information.\n"
            "- For food orders, use request_my_food_order.\n"
            "- Never invent additional confirmation requirements.\n"
            "- Never claim an order is placed when approval is pending.\n"
            "- Clearly communicate rejected requests and their reasons.\n"
            "- If information is unavailable, say so honestly.\n\n"

            "BREAKFAST-SPECIFIC RULES:\n"
            "- There is no separate breakfast catalogue in your data.\n"
            "- If asked about breakfast, report only actual menu items.\n"
            "- Do not assume an item is served during breakfast.\n"
            "- Never invent breakfast serving hours.\n"
            "- Never invent eggs, bacon, sausages, yogurt or other foods.\n"
            "- Explain that breakfast-specific information is not available "
            "if the guest asks for details not present in the menu.\n"
        )
    )

    print("\nPASS: Booking Specialist created")
    print("PASS: Kitchen Specialist created")

    return booking_agent, kitchen_agent
