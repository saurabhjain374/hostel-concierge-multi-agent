
import asyncio

from src.orchestrator.orchestrator import (
    create_hostel_orchestrator
)


async def main():

    orchestrator = await create_hostel_orchestrator(
        guest_id="G003"
    )

    conversation = [
        {
            "role": "user",
            "content": "I want to check out. Please initiate my checkout."
        }
    ]

    print("\nSTEP 1: Already checked-out guest requests checkout")

    result = await orchestrator.ainvoke({
        "messages": conversation
    })

    response = result["messages"][-1].content

    print("\nORCHESTRATOR RESPONSE:")
    print(response)

    # No approval request should be created.
    assert orchestrator.pending_approval_request_id is None, (
        "FAIL: A checked-out guest must not receive a pending request."
    )

    print("\nPASS: No checkout approval request created.")

    # Verify that the response communicates the rejection.
    assert (
        "checked out" in response.lower()
        or "only checked-in" in response.lower()
        or "cannot" in response.lower()
        or "not eligible" in response.lower()
    ), "FAIL: Checkout rejection was not communicated."

    print("PASS: Checkout restriction communicated.")
    print("\nALL CHECKED-OUT GUEST TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(main())
