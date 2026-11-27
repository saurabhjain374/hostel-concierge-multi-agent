
import uuid
from datetime import datetime, timezone


class ApprovalManager:
    """
    In-memory approval manager for checkout and food orders.

    Responsibilities:
    - Create approval requests.
    - Retrieve individual and pending requests.
    - Filter pending requests by guest.
    - Approve or reject requests.
    - Enforce guest ownership before decisions.
    - Prevent duplicate decisions.
    """

    def __init__(self):
        self.pending_requests = {}

    # -------------------------------------------------
    # 1. Create approval request
    # -------------------------------------------------

    def create_request(self, request_data: dict) -> dict:
        """Register a new request that requires guest approval."""

        if request_data.get("status") != "pending_approval":
            raise ValueError(
                "Only pending approval requests can be registered."
            )

        guest_id = request_data.get("guest_id")

        if not guest_id:
            raise ValueError(
                "Guest ID is required for an approval request."
            )

        request_id = request_data.get("request_id")

        if not request_id:
            request_id = str(uuid.uuid4())

        if request_id in self.pending_requests:
            raise ValueError("Request already exists.")

        request = {
            **request_data,
            "request_id": request_id,
            "approval_status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "decision_at": None,
            "decision": None
        }

        self.pending_requests[request_id] = request

        return request.copy()

    # -------------------------------------------------
    # 2. Retrieve approval request
    # -------------------------------------------------

    def get_request(self, request_id: str) -> dict | None:
        """Retrieve an approval request by its ID."""

        request = self.pending_requests.get(request_id)

        if not request:
            return None

        return request.copy()

    # -------------------------------------------------
    # 3. Retrieve pending requests
    # -------------------------------------------------

    def get_pending_requests(
        self,
        guest_id: str | None = None
    ) -> list[dict]:
        """
        Retrieve pending requests.

        If guest_id is provided, return only that guest's requests.
        """

        requests = []

        for request in self.pending_requests.values():

            if request["approval_status"] != "pending":
                continue

            if (
                guest_id is not None
                and request.get("guest_id") != guest_id
            ):
                continue

            requests.append(request.copy())

        return requests

    # -------------------------------------------------
    # 4. Approve or reject request
    # -------------------------------------------------

    def decide(
        self,
        request_id: str,
        approved: bool,
        guest_id: str
    ) -> dict:
        """
        Approve or reject a pending request.

        Only the guest who owns the request can make
        the approval decision.
        """

        request = self.pending_requests.get(request_id)

        if not request:
            return {
                "status": "error",
                "message": "Approval request not found."
            }

        # Enforce guest ownership.
        if request.get("guest_id") != guest_id:
            return {
                "status": "error",
                "message": (
                    "You are not authorized to decide this request."
                )
            }

        # Prevent duplicate decisions.
        if request["approval_status"] != "pending":
            return {
                "status": "error",
                "message": (
                    "This request has already been decided."
                )
            }

        decision = "approved" if approved else "rejected"

        request["approval_status"] = decision
        request["decision"] = decision
        request["decision_at"] = (
            datetime.now(timezone.utc).isoformat()
        )

        if approved:
            request["execution_status"] = "simulated_completed"
        else:
            request["execution_status"] = "cancelled"

        return {
            "status": decision,
            "request_id": request_id,
            "action": request.get("action"),
            "guest_id": request.get("guest_id"),
            "execution_status": request["execution_status"],
            "message": (
                "Request approved. Simulated execution completed."
                if approved
                else "Request rejected. No action was executed."
            )
        }
