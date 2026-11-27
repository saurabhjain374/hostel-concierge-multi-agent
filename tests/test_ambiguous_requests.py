
import asyncio

from langchain_core.messages import AIMessage

from src.orchestrator.orchestrator import HostelOrchestrator


class UnusedAgent:
    async def ainvoke(self, state, config=None):
        raise AssertionError(
            "A specialist should not be invoked for an ambiguous request."
        )


async def verify_unspecified_food_order():
    orchestrator = HostelOrchestrator(
        guest_id="G001",
        booking_agent=UnusedAgent(),
        kitchen_agent=UnusedAgent()
    )

    result = await orchestrator.ainvoke({
        "messages": [
            {
                "role": "user",
                "content": "I want to order food"
            }
        ]
    })

    response = result["messages"][-1].content

    assert isinstance(result["messages"][-1], AIMessage)
    assert "which food item" in response.lower()
    print("PASS: Unspecified food order requests clarification.")


async def verify_unspecified_request():
    orchestrator = HostelOrchestrator(
        guest_id="G001",
        booking_agent=UnusedAgent(),
        kitchen_agent=UnusedAgent()
    )

    result = await orchestrator.ainvoke({
        "messages": [
            {
                "role": "user",
                "content": "Can you help me?"
            }
        ]
    })

    response = result["messages"][-1].content

    assert isinstance(result["messages"][-1], AIMessage)
    assert "booking" in response.lower()
    assert "kitchen" in response.lower()
    print("PASS: Unclear general requests receive available-service guidance.")


async def main():
    await verify_unspecified_food_order()
    await verify_unspecified_request()

    print("\nALL AMBIGUOUS REQUEST TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(main())
