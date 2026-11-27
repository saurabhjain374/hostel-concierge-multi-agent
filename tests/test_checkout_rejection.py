
import asyncio

from src.orchestrator.orchestrator import (
    create_hostel_orchestrator
)


async def main():

    orchestrator = await create_hostel_orchestrator(
        guest_id="G001"
    )

    # Step 1: Submit checkout request.
    conversation = [
        {
            "role": "user",
            "content": "Please initiate my checkout."
        }
    ]

    print("\nSTEP 1: Guest requests checkout")

    result = await orchestrator.ainvoke({
        "messages": conversation
    })

    conversation = result["messages"]

    request_id = orchestrator.pending_approval_request_id

    assert request_id is not None

    print(conversation[-1].content)
    print("\nPASS: Checkout request created.")

    # Step 2: Guest rejects the request.
    print("\nSTEP 2: Guest rejects checkout")

    conversation.append({
        "role": "user",
        "content": "REJECT"
    })

    result = await orchestrator.ainvoke({
        "messages": conversation
    })

    conversation = result["messages"]

    print(conversation[-1].content)

    assert orchestrator.pending_approval_request_id is None

    request = orchestrator.approval_manager.get_request(
    request_id
)

    assert request is not None, "Approval request was not found."

    assert request["approval_status"] == "rejected"
    assert request["execution_status"] == "cancelled"

    print("\nPASS: Checkout request rejected.")
    print("PASS: No checkout action executed.")
    print("PASS: Pending approval state cleared.")

    print("\nALL CHECKOUT REJECTION TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(main())
