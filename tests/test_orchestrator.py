
import asyncio

from src.orchestrator.orchestrator import create_hostel_orchestrator


async def main():
    orchestrator = await create_hostel_orchestrator(
        guest_id="G001"
    )

    question = (
    "I would like to know my checkout date and "
    "what breakfast items are available."
)

    print(f"\nGUEST: {question}")

    result = await orchestrator.ainvoke({
        "messages": [
            {"role": "user", "content": question}
        ]
    })

    print("\n========== EXECUTION TRACE ==========")

    for index, message in enumerate(result["messages"], start=1):
        print(f"\nMESSAGE {index}")
        print(f"TYPE: {type(message).__name__}")

        if isinstance(message, dict):
            content = message.get("content", "")
        else:
            content = getattr(message, "content", "")

        print(f"CONTENT: {content}")

    print("\n========== FINAL RESPONSE ==========")

    last_message = result["messages"][-1]

    if isinstance(last_message, dict):
        print(last_message.get("content", ""))
    else:
        print(last_message.content)


if __name__ == "__main__":
    asyncio.run(main())
