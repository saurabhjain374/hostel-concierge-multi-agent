
import asyncio

from src.orchestrator.orchestrator import (
    create_hostel_orchestrator
)


async def run_checkout_approval_test():

    orchestrator = await create_hostel_orchestrator(
        guest_id="G001"
    )

    conversation = [
        {
            "role": "user",
            "content": "I want to check out. Please initiate my checkout."
        }
    ]

    # STEP 1: Guest requests checkout.
    print("\n========== STEP 1: CHECKOUT REQUEST ==========")

    result = await orchestrator.ainvoke({
        "messages": conversation
    })

    conversation = result["messages"]

    print(conversation[-1].content)

    # Verify that an approval request was created.
    request_id = orchestrator.pending_approval_request_id

    assert request_id is not None, (
        "FAIL: No pending checkout approval request was created."
    )

    print("\nPASS: Checkout request is pending approval.")
    print(f"Request ID: {request_id}")

    # STEP 2: Guest approves checkout.
    print("\n========== STEP 2: GUEST APPROVES ==========")

    conversation.append({
        "role": "user",
        "content": "APPROVE"
    })

    result = await orchestrator.ainvoke({
        "messages": conversation
    })

    conversation = result["messages"]

    print(conversation[-1].content)

    assert orchestrator.pending_approval_request_id is None

    assert "approved" in conversation[-1].content.lower()

    print("\nPASS: Checkout approval processed.")
    print("PASS: Pending approval state cleared.")

    print("\nALL CHECKOUT APPROVAL TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(run_checkout_approval_test())
