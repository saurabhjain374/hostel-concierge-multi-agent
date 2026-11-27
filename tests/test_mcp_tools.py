
import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent


def get_tool_text(result) -> str:
    """Safely extract text from an MCP tool response."""
    for content in result.content:
        if isinstance(content, TextContent):
            return content.text

    raise ValueError("MCP tool response contains no text content")


async def main():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.mcp_server.server"]
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:

            await session.initialize()

            # Test 1: Discover all four MCP tools
            tools = await session.list_tools()
            tool_names = {tool.name for tool in tools.tools}

            expected_tools = {
                "get_guest_booking",
                "request_checkout",
                "get_menu",
                "request_food_order"
            }

            assert expected_tools.issubset(tool_names)
            print("PASS: All four MCP tools discovered")

            # Test 2: Read guest booking
            result = await session.call_tool(
                "get_guest_booking",
                arguments={"guest_id": "G001"}
            )

            booking = json.loads(get_tool_text(result))

            assert booking["guest_id"] == "G001"
            assert booking["room_number"] == "101"
            assert booking["booking"]["status"] == "checked_in"

            print("PASS: Guest booking retrieved")

            # Test 3: Checkout requires approval
            result = await session.call_tool(
                "request_checkout",
                arguments={"guest_id": "G001"}
            )

            checkout = json.loads(get_tool_text(result))

            assert checkout["status"] == "pending_approval"
            assert checkout["action"] == "checkout"

            print("PASS: Checkout request requires approval")

            # Test 4: Checked-out guest cannot request checkout
            result = await session.call_tool(
                "request_checkout",
                arguments={"guest_id": "G003"}
            )

            rejected_checkout = json.loads(get_tool_text(result))

            assert rejected_checkout["status"] == "rejected"

            print("PASS: Checkout rejected for checked-out guest")

            # Test 5: Retrieve menu, stock and allergens
            result = await session.call_tool(
                "get_menu",
                arguments={}
            )

            menu_data = json.loads(get_tool_text(result))
            menu = menu_data["menu"]

            assert any(
                item["item_id"] == "M005" and not item["available"]
                for item in menu
            )

            assert any(
                "peanuts" in item["allergens"]
                for item in menu
            )

            print("PASS: Menu, stock and allergen information retrieved")

            # Test 6: Out-of-stock food cannot be ordered
            result = await session.call_tool(
                "request_food_order",
                arguments={
                    "guest_id": "G001",
                    "item_id": "M005",
                    "quantity": 1
                }
            )

            rejected_order = json.loads(get_tool_text(result))

            assert rejected_order["status"] == "rejected"
            assert "out of stock" in rejected_order["reason"].lower()

            print("PASS: Out-of-stock order rejected")

            # Test 7: Valid food order follows kitchen and approval rules
            result = await session.call_tool(
                "request_food_order",
                arguments={
                    "guest_id": "G001",
                    "item_id": "M001",
                    "quantity": 2
                }
            )

            food_order = json.loads(get_tool_text(result))

            if menu_data["kitchen_open"]:
                assert food_order["status"] == "pending_approval"
                assert food_order["total_price"] == 240

                print("PASS: Valid food order requires approval")
            else:
                assert food_order["status"] == "rejected"

                print("PASS: Food order rejected because kitchen is closed")

            print("\nAll MCP integration checks passed!")


if __name__ == "__main__":
    asyncio.run(main())
