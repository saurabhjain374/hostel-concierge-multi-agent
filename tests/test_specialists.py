
from src.agents.specialists import create_specialist_toolsets


def main():
    guest_id = "G001"

    # Dummy MCP tools: sufficient to create wrappers,
    # without starting another MCP server.
    dummy_tool_map = {
        "get_guest_booking": None,
        "request_checkout": None,
        "get_menu": None,
        "request_food_order": None,
    }

    booking_tools, kitchen_tools = create_specialist_toolsets(
        guest_id,
        dummy_tool_map
    )

    booking_names = {tool.name for tool in booking_tools}
    kitchen_names = {tool.name for tool in kitchen_tools}

    expected_booking = {
        "get_my_booking",
        "request_my_checkout",
    }

    expected_kitchen = {
        "get_kitchen_menu",
        "request_my_food_order",
    }

    assert booking_names == expected_booking
    assert kitchen_names == expected_kitchen

    assert booking_names.isdisjoint(kitchen_names)

    print("PASS: Booking Specialist has only Booking tools.")
    print("PASS: Kitchen Specialist has only Kitchen tools.")
    print("PASS: No cross-specialist tool access.")

    print("\nALL SPECIALIST ISOLATION TESTS PASSED!")


if __name__ == "__main__":
    main()
