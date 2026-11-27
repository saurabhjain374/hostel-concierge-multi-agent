
from src.agents.specialists import create_specialist_toolsets


class MockMCPTool:
    """Simulate an MCP tool and count actual executions."""

    def __init__(self, name):
        self.name = name
        self.calls = 0

    async def ainvoke(self, args):
        self.calls += 1
        return {"status": "success", "tool": self.name}


async def main():

    # Create mock MCP tools
    mock_tools = {
        "get_guest_booking": MockMCPTool("get_guest_booking"),
        "request_checkout": MockMCPTool("request_checkout"),
        "get_menu": MockMCPTool("get_menu"),
        "request_food_order": MockMCPTool("request_food_order"),
    }

    booking_tools, kitchen_tools, booking_counter, kitchen_counter = (
        create_specialist_toolsets("G001", mock_tools)
    )

    booking_tool_map = {
        specialist_tool.name: specialist_tool
        for specialist_tool in booking_tools
    }

    kitchen_tool_map = {
        specialist_tool.name: specialist_tool
        for specialist_tool in kitchen_tools
    }

    # -------------------------------------------------
    # Test Booking Specialist limit
    # -------------------------------------------------

    for _ in range(2):
        await booking_tool_map["get_my_booking"].ainvoke({})

    for _ in range(2):
        await booking_tool_map["request_my_checkout"].ainvoke({})

    assert booking_counter.calls == 4

    # Fifth execution must be blocked
    result = await booking_tool_map["get_my_booking"].ainvoke({})

    assert "TOOL CALL LIMIT REACHED" in result
    assert mock_tools["get_guest_booking"].calls == 2
    assert mock_tools["request_checkout"].calls == 2

    print("PASS: Booking Specialist blocks its fifth MCP tool execution.")

    # -------------------------------------------------
    # Test Kitchen Specialist limit
    # -------------------------------------------------

    for _ in range(2):
        await kitchen_tool_map["get_kitchen_menu"].ainvoke({})

    for _ in range(2):
        await kitchen_tool_map["request_my_food_order"].ainvoke({
            "item_id": "M001",
            "quantity": 1
        })

    assert kitchen_counter.calls == 4

    # Fifth execution must be blocked
    result = await kitchen_tool_map["get_kitchen_menu"].ainvoke({})

    assert "TOOL CALL LIMIT REACHED" in result
    assert mock_tools["get_menu"].calls == 2
    assert mock_tools["request_food_order"].calls == 2

    print("PASS: Kitchen Specialist blocks its fifth MCP tool execution.")

    # -------------------------------------------------
    # Verify independent counters
    # -------------------------------------------------

    assert booking_counter.calls == 4
    assert kitchen_counter.calls == 4

    print("PASS: Booking and Kitchen counters are independent.")

    # -------------------------------------------------
    # Verify reset functionality
    # -------------------------------------------------

    booking_counter.reset()

    await booking_tool_map["get_my_booking"].ainvoke({})

    assert booking_counter.calls == 1
    assert mock_tools["get_guest_booking"].calls == 3

    print("PASS: Booking counter resets for a new invocation.")

    print("\nALL TOOL CALL LIMIT TESTS PASSED!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
