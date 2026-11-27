
import asyncio

from langchain_core.messages import AIMessage

from src.orchestrator.orchestrator import HostelOrchestrator


class UnusedAgent:
    async def ainvoke(self, state, config=None):
        raise AssertionError(
            "Specialists should not be invoked for out-of-scope requests."
        )


async def main():
    orchestrator = HostelOrchestrator(
        guest_id="G001",
        booking_agent=UnusedAgent(),
        kitchen_agent=UnusedAgent()
    )

    result = await orchestrator.ainvoke({
        "messages": [
            {
                "role": "user",
                "content": "What will the weather be like tomorrow?"
            }
        ]
    })

    response = result["messages"][-1].content

    assert isinstance(result["messages"][-1], AIMessage)
    assert "can't help" in response.lower() or "cannot help" in response.lower()
    assert "booking" in response.lower()
    assert "kitchen" in response.lower()

    print("PASS: Weather request declined as out of scope.")
    print("PASS: No specialist was invoked.")
    print("\nALL OUT-OF-SCOPE TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(main())
