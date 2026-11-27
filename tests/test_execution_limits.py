
import asyncio

from langgraph.errors import GraphRecursionError

from src.orchestrator.orchestrator import HostelOrchestrator


class LimitReachedAgent:
    """Mock specialist that simulates LangGraph reaching its recursion limit."""

    def __init__(self):
        self.received_config = None

    async def ainvoke(self, state, config=None):
        self.received_config = config
        raise GraphRecursionError("Simulated execution limit reached")


async def verify_booking_limit():
    booking_agent = LimitReachedAgent()
    kitchen_agent = LimitReachedAgent()

    orchestrator = HostelOrchestrator(
        guest_id="G001",
        booking_agent=booking_agent,
        kitchen_agent=kitchen_agent
    )

    result = await orchestrator.ainvoke({
        "messages": [
            {
                "role": "user",
                "content": "Show my booking details"
            }
        ]
    })

    response = result["messages"][-1].content

    assert booking_agent.received_config is not None, (
        "Booking Specialist did not receive execution configuration."
    )
    assert booking_agent.received_config.get("recursion_limit") == 12
    assert "execution limit" in response.lower()

    # Booking-only requests must not invoke the Kitchen Specialist.
    assert kitchen_agent.received_config is None

    print("PASS: Booking Specialist execution limit enforced.")
    print("PASS: Booking request did not invoke Kitchen Specialist.")


async def verify_kitchen_limit():
    booking_agent = LimitReachedAgent()
    kitchen_agent = LimitReachedAgent()

    orchestrator = HostelOrchestrator(
        guest_id="G001",
        booking_agent=booking_agent,
        kitchen_agent=kitchen_agent
    )

    result = await orchestrator.ainvoke({
        "messages": [
            {
                "role": "user",
                "content": "Show me the kitchen menu"
            }
        ]
    })

    response = result["messages"][-1].content

    assert kitchen_agent.received_config is not None, (
        "Kitchen Specialist did not receive execution configuration."
    )
    assert kitchen_agent.received_config.get("recursion_limit") == 12
    assert "execution limit" in response.lower()

    # Kitchen-only requests must not invoke the Booking Specialist.
    assert booking_agent.received_config is None

    print("PASS: Kitchen Specialist execution limit enforced.")
    print("PASS: Kitchen request did not invoke Booking Specialist.")


async def main():
    await verify_booking_limit()
    await verify_kitchen_limit()

    print("\nALL EXECUTION LIMIT TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(main())
