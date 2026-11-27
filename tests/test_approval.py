
from src.approval import ApprovalManager


def test_approval_manager():

    manager = ApprovalManager()

    request = manager.create_request({
        "status": "pending_approval",
        "request_id": "REQ001",
        "action": "checkout",
        "guest_id": "G001",
        "room_number": "101"
    })

    assert request["approval_status"] == "pending"

    # Pending request is retrievable.
    retrieved = manager.get_request("REQ001")
    assert retrieved is not None
    assert retrieved["request_id"] == "REQ001"

    # Pending requests can be filtered by guest.
    pending = manager.get_pending_requests("G001")
    assert len(pending) == 1

    # Approve request.
    decision = manager.decide(
        "REQ001",
        approved=True,
        guest_id="G001"
    )

    assert decision["status"] == "approved"
    assert decision["execution_status"] == "simulated_completed"

    # Request should no longer be pending.
    assert manager.get_pending_requests("G001") == []

    # Cannot approve/reject a previously decided request.
    duplicate = manager.decide(
        "REQ001",
        approved=False,
        guest_id="G001"
    )
    assert duplicate["status"] == "error"

    # Rejection test.
    manager.create_request({
        "status": "pending_approval",
        "request_id": "REQ002",
        "action": "food_order",
        "guest_id": "G001"
    })

    rejection = manager.decide(
        "REQ002",
        approved=False,
        guest_id="G001"
    )

    assert rejection["status"] == "rejected"
    assert rejection["execution_status"] == "cancelled"

    # Unknown request test.
    unknown = manager.decide(
        "UNKNOWN",
        approved=True,
        guest_id="G001"
    )
    assert unknown["status"] == "error"

    print("PASS: Approval request creation")
    print("PASS: Pending request retrieval")
    print("PASS: Guest-specific pending requests")
    print("PASS: Request approval")
    print("PASS: Request rejection")
    print("PASS: Duplicate decision prevention")
    print("PASS: Unknown request rejection")


def test_cross_guest_approval_security():

    manager = ApprovalManager()

    # G001 creates a checkout approval request.
    request = manager.create_request({
        "status": "pending_approval",
        "request_id": "REQ-SEC-001",
        "action": "checkout",
        "guest_id": "G001",
        "room_number": "101"
    })

    # G002 attempts to approve G001's request.
    result = manager.decide(
        request_id=request["request_id"],
        approved=True,
        guest_id="G002"
    )

    assert result["status"] == "error"

    # Request must remain pending.
    updated_request = manager.get_request(
        request["request_id"]
    )

    assert updated_request is not None
    assert updated_request["approval_status"] == "pending"

    print("PASS: G002 cannot approve G001's request.")
    print("PASS: Unauthorized approval leaves request pending.")


if __name__ == "__main__":
    test_approval_manager()
    test_cross_guest_approval_security()

    print("\nALL APPROVAL MANAGER TESTS PASSED!")
