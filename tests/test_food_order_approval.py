
import asyncio

from src.orchestrator.orchestrator import create_hostel_orchestrator


async def main():
    orchestrator = await create_hostel_orchestrator(guest_id="G001")

    conversation = [
        {
            "role": "user",
            "content": "I would like to order one Veg Sandwich."
        }
    ]

    print("\nSTEP 1: Guest requests a food order")

    result = await orchestrator.ainvoke({
        "messages": conversation
    })

    response = result["messages"][-1].content

    print("\nORCHESTRATOR RESPONSE:")
    print(response)

    request_id = orchestrator.pending_approval_request_id

    assert request_id is not None, (
        "FAIL: Food order should create a pending approval request."
    )

    request = orchestrator.approval_manager.get_request(request_id)

    assert request is not None
    assert request["action"] == "food_order"
    assert request["approval_status"] == "pending"

    print("\nPASS: Food order approval request created.")
    print("PASS: Order is awaiting guest approval.")

    print("\nSTEP 2: Guest approves the food order")

    conversation.append({
        "role": "assistant",
        "content": response
    })

    conversation.append({
        "role": "user",
        "content": "APPROVE"
    })

    result = await orchestrator.ainvoke({
        "messages": conversation
    })

    final_response = result["messages"][-1].content

    print("\nORCHESTRATOR RESPONSE:")
    print(final_response)

    updated_request = orchestrator.approval_manager.get_request(request_id)

    assert updated_request is not None, (
            "FAIL: Could not retrieve the updated food order request."
        )

    assert updated_request["approval_status"] == "approved"
    assert updated_request["execution_status"] == "simulated_completed"

    print("\nPASS: Food order approved.")
    print("PASS: Simulated order workflow completed.")
    print("\nALL FOOD ORDER APPROVAL TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(main())
