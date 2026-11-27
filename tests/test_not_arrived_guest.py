
import asyncio

from src.orchestrator.orchestrator import (
    create_hostel_orchestrator
)


async def main():

    # G004 is Neha, whose booking status is not_arrived.
    orchestrator = await create_hostel_orchestrator(
        guest_id="G004"
    )

    # Scenario 1: Checkout request
    print("\nSTEP 1: Not-arrived guest requests checkout")

    result = await orchestrator.ainvoke({
        "messages": [
            {
                "role": "user",
                "content": "I want to check out. Please initiate my checkout."
            }
        ]
    })

    response = result["messages"][-1].content

    print("\nORCHESTRATOR RESPONSE:")
    print(response)

    assert orchestrator.pending_approval_request_id is None, (
        "FAIL: A not-arrived guest must not receive checkout approval."
    )

    assert (
        "not arrived" in response.lower()
        or "not eligible" in response.lower()
        or "cannot" in response.lower()
        or "only checked-in" in response.lower()
    ), "FAIL: Checkout restriction was not communicated."

    print("\nPASS: Checkout request rejected.")
    print("PASS: No checkout approval request created.")

    # Scenario 2: Food order request
    print("\nSTEP 2: Not-arrived guest requests food")

    result = await orchestrator.ainvoke({
        "messages": [
            {
                "role": "user",
                "content": "I would like to order one Veg Sandwich."
            }
        ]
    })

    response = result["messages"][-1].content

    print("\nORCHESTRATOR RESPONSE:")
    print(response)

    assert orchestrator.pending_approval_request_id is None, (
        "FAIL: A not-arrived guest must not receive food order approval."
    )

    assert (
        "not arrived" in response.lower()
        or "not eligible" in response.lower()
        or "cannot" in response.lower()
        or "only checked-in" in response.lower()
    ), "FAIL: Food order restriction was not communicated."

    print("\nPASS: Food order request rejected.")
    print("PASS: No food order approval request created.")

    print("\nALL NOT-ARRIVED GUEST TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(main())
