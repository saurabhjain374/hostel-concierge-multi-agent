
import asyncio
import ast

from src.agents.specialists import create_specialist_toolsets


class DummyMCPTool:
    """Simulates an MCP tool and records its arguments."""

    def __init__(self):
        self.calls = []

    async def ainvoke(self, arguments):
        self.calls.append(arguments)

        guest_id = arguments.get("guest_id")

        if guest_id == "G001":
            return {
                "guest_id": "G001",
                "name": "Rahul",
                "room_number": 101
            }

        if guest_id == "G002":
            return {
                "guest_id": "G002",
                "name": "Priya",
                "room_number": 102
            }

        return {"error": "Guest not found"}


async def main():

    # Simulate MCP tools.
    mock_booking_tool = DummyMCPTool()

    tool_map = {
        "get_guest_booking": mock_booking_tool,
        "request_checkout": DummyMCPTool(),
        "get_menu": DummyMCPTool(),
        "request_food_order": DummyMCPTool(),
    }

    # Application authenticates Rahul as G001.
    authenticated_guest_id = "G001"

    booking_tools, kitchen_tools = create_specialist_toolsets(
        authenticated_guest_id,
        tool_map
    )

    # Find the guest-scoped booking tool.
    get_my_booking = next(
        tool for tool in booking_tools
        if tool.name == "get_my_booking"
    )

    print("\nSTEP 1: Authenticated guest requests booking")

    result = await get_my_booking.ainvoke({})

    print("\nBOOKING TOOL RESPONSE:")
    print(result)

    # Convert the tool's string response into a dictionary.
    parsed_result = (
            ast.literal_eval(result)
            if isinstance(result, str)
            else result
        )

# Verify that the MCP call used the authenticated guest ID.
    assert mock_booking_tool.calls[-1]["guest_id"] == "G001", (
    "FAIL: Booking tool did not use the authenticated guest ID."
)

    assert parsed_result["guest_id"] == "G001"
    assert parsed_result["name"] == "Rahul"
    assert parsed_result["room_number"] == 101

    print("\nPASS: Rahul's booking retrieved.")
    print("PASS: Application supplied authenticated guest ID G001.")

    # Verify that the tool does not expose guest_id as an input.
    tool_schema = get_my_booking.args

    assert "guest_id" not in tool_schema, (
        "FAIL: Guest ID must not be an input to the specialist tool."
    )

    print("PASS: Guest cannot supply another guest ID to the tool.")

    # Verify that the toolsets remain isolated.
    booking_names = {tool.name for tool in booking_tools}
    kitchen_names = {tool.name for tool in kitchen_tools}

    assert booking_names.isdisjoint(kitchen_names)

    print("PASS: Booking and Kitchen toolsets remain isolated.")

    print("\nALL GUEST ISOLATION TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(main())
