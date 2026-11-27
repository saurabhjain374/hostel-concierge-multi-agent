
from langchain_core.messages import AIMessage
from src.orchestrator.orchestrator import HostelOrchestrator


class UnusedAgent:
    async def ainvoke(self, state, config=None):
        raise AssertionError("Specialist should not be invoked")


async def main():
    orchestrator = HostelOrchestrator(
        guest_id="G001",
        booking_agent=UnusedAgent(),
        kitchen_agent=UnusedAgent()
    )

    # First conversation turn
    first_result = await orchestrator.ainvoke({
        "messages": [
            {
                "role": "user",
                "content": "Hello"
            }
        ]
    })

    first_history = first_result["messages"]

    assert len(first_history) == 2
    assert first_history[0]["content"] == "Hello"
    assert isinstance(first_history[1], AIMessage)

    # Second turn uses the history returned by the first turn.
    second_result = await orchestrator.ainvoke({
        "messages": first_history + [
            {
                "role": "user",
                "content": "What services can you provide?"
            }
        ]
    })

    second_history = second_result["messages"]

    assert len(second_history) == 4
    assert second_history[0]["content"] == "Hello"
    assert second_history[2]["content"] == (
        "What services can you provide?"
    )
    assert isinstance(second_history[3], AIMessage)

    print("PASS: First conversation turn stored.")
    print("PASS: Previous conversation history preserved.")
    print("PASS: Second conversation turn appended.")
    print("\nALL CONVERSATION MEMORY TESTS PASSED!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
