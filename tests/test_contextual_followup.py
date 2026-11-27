
import asyncio
import json

from langchain_core.messages import AIMessage, ToolMessage

from src.orchestrator.orchestrator import HostelOrchestrator


class MockAgent:
    def __init__(self):
        self.calls = 0
        self.last_instruction: str = ""

    async def ainvoke(self, state, config=None):
        self.calls += 1
        self.last_instruction = state["messages"][-1]["content"]

        # First invocation: return the kitchen menu.
        if self.calls == 1:
            tool_name = "get_kitchen_menu"
            result = {
                "kitchen_open": True,
                "menu": [
                    {
                        "item_id": "M001",
                        "name": "Veg Sandwich",
                        "price": 120,
                        "available": True,
                        "allergens": []
                    }
                ]
            }

        # Second invocation: simulate a pending food order.
        else:
            tool_name = "request_my_food_order"
            result = {
                "status": "pending_approval",
                "guest_id": "G001",
                "name": "Rahul",
                "room_number": 101,
                "action": "food_order",
                "item_id": "M001",
                "quantity": 1,
                "total_price": 120
            }

        return {
            "messages": [
                ToolMessage(
                    content=json.dumps(result),
                    tool_call_id=f"mock-call-{self.calls}",
                    name=tool_name
                )
            ]
        }


async def main():
    booking_agent = MockAgent()
    kitchen_agent = MockAgent()

    orchestrator = HostelOrchestrator(
        guest_id="G001",
        booking_agent=booking_agent,
        kitchen_agent=kitchen_agent
    )

    # Turn 1: Ask whether Veg Sandwich is available.
    first_result = await orchestrator.ainvoke({
        "messages": [
            {
                "role": "user",
                "content": "Is Veg Sandwich available?"
            }
        ]
    })

    first_history = first_result["messages"]
    first_response = first_history[-1].content

    assert isinstance(first_history[-1], AIMessage)
    assert "KITCHEN INFORMATION" in first_response
    assert "Veg Sandwich" in first_response

    print("PASS: First turn retrieves kitchen information.")

    # Turn 2: Refer to the previously mentioned food item.
    second_result = await orchestrator.ainvoke({
        "messages": first_history + [
            {
                "role": "user",
                "content": "Can I order that?"
            }
        ]
    })

    second_response = second_result["messages"][-1].content

    assert "FOOD ORDER APPROVAL REQUIRED" in second_response
    assert "Veg Sandwich" in second_response
    assert "Item ID: M001" in kitchen_agent.last_instruction
    assert kitchen_agent.calls == 2

    print("PASS: Follow-up resolves 'that' to Veg Sandwich.")
    print("PASS: Correct food item ID is sent to Kitchen Specialist.")
    print("PASS: Food order approval is requested.")

    print("\nALL CONTEXTUAL FOLLOW-UP TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(main())
