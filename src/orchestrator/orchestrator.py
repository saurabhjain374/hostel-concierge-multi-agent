
import ast
import json
import re

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.errors import GraphRecursionError

from src.agents.specialists import create_specialist_agents
from src.approval import ApprovalManager


class HostelOrchestrator:

    MENU_ITEMS = {
        "veg sandwich": "M001",
        "paneer wrap": "M002",
        "peanut butter toast": "M003",
        "masala dosa": "M004",
        "veg burger": "M005",
        "fruit bowl": "M006",
        "coffee": "M007"
    }

    def __init__(
        self,
        guest_id: str,
        booking_agent,
        kitchen_agent,
        booking_counter=None,
        kitchen_counter=None
    ):
        self.guest_id = guest_id
        self.booking_agent = booking_agent
        self.kitchen_agent = kitchen_agent

        self.booking_counter = booking_counter
        self.kitchen_counter = kitchen_counter

        self.approval_manager = ApprovalManager()
        self.pending_approval_request_id = None

    # -------------------------------------------------
    # Message helpers
    # -------------------------------------------------

    def _get_message_content(self, message) -> str:

        if isinstance(message, dict):
            return str(message.get("content", ""))

        return str(getattr(message, "content", ""))

    def _is_user_message(self, message) -> bool:

        if isinstance(message, dict):
            return message.get("role") in ("user", "human")

        return getattr(message, "type", None) == "human"

    def _contains_keyword(self, text: str, keyword: str) -> bool:

        pattern = (
            r"(?<!\w)"
            + re.escape(keyword)
            + r"(?!\w)"
        )

        return re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        ) is not None

    def _reset_counter(self, counter):

        if counter is not None:
            counter.reset()

    def _resolve_food_item_from_history(
        self,
        messages: list,
        current_message: str
    ) -> tuple[str | None, str | None]:

        # First check whether the current message explicitly
        # mentions a menu item.
        current_text = current_message.lower()

        for item_name, item_id in self.MENU_ITEMS.items():

            if self._contains_keyword(current_text, item_name):
                return item_id, item_name

        # If the current message does not mention an item,
        # inspect previous USER messages only.
        #
        # Assistant responses may contain the entire menu.
        # Using them could incorrectly infer an unrelated item.

        for message in reversed(messages):

            if not self._is_user_message(message):
                continue

            content = self._get_message_content(message).lower()

            for item_name, item_id in self.MENU_ITEMS.items():

                if self._contains_keyword(content, item_name):
                    return item_id, item_name

        return None, None

    def _extract_tool_results(
        self,
        agent_result,
        expected_tool_names: set[str]
    ) -> list[dict]:

        results = []

        agent_messages = agent_result.get("messages", [])

        for message in agent_messages:

            if not isinstance(message, ToolMessage):
                continue

            if message.name not in expected_tool_names:
                continue

            content = message.content

            if isinstance(content, str):

                try:
                    parsed_content = json.loads(content)

                except json.JSONDecodeError:

                    try:
                        parsed_content = ast.literal_eval(content)

                    except (ValueError, SyntaxError):
                        continue

            else:
                parsed_content = content

            if isinstance(parsed_content, list):

                for block in parsed_content:

                    if not isinstance(block, dict):
                        continue

                    block_text = block.get("text")

                    if not block_text:
                        continue

                    try:
                        parsed_result = json.loads(block_text)

                    except (json.JSONDecodeError, TypeError):
                        continue

                    if isinstance(parsed_result, dict):
                        results.append(parsed_result)

            elif isinstance(parsed_content, dict):

                results.append(parsed_content)

        return results

    # -------------------------------------------------
    # Booking formatting
    # -------------------------------------------------

    def _format_booking(self, tool_results: list[dict]) -> str:

        if not tool_results:
            return "Unable to retrieve your booking information."

        guest = tool_results[-1]

        if guest.get("error"):
            return guest["error"]

        booking = guest.get("booking", {})

        return (
            "BOOKING INFORMATION:\n\n"
            f"Guest: {guest.get('name', 'N/A')}\n"
            f"Room: {guest.get('room_number', 'N/A')}\n"
            f"Check-in date: {booking.get('check_in', 'N/A')}\n"
            f"Checkout date: {booking.get('check_out', 'N/A')}\n"
            f"Booking status: {booking.get('status', 'N/A')}"
        )

    # -------------------------------------------------
    # Kitchen formatting
    # -------------------------------------------------

    def _format_kitchen(self, tool_results: list[dict]) -> str:

        if not tool_results:
            return "Unable to retrieve kitchen information."

        kitchen = tool_results[-1]

        if kitchen.get("status") == "error":
            return kitchen.get(
                "reason",
                "Unable to retrieve kitchen information."
            )

        kitchen_open = kitchen.get("kitchen_open", False)

        lines = [
            "KITCHEN INFORMATION:",
            "",
            f"Kitchen status: {'Open' if kitchen_open else 'Closed'}",
            "",
            "Menu items:"
        ]

        for item in kitchen.get("menu", []):

            availability = (
                "Available"
                if item.get("available")
                else "Out of stock"
            )

            line = (
                f"- {item.get('name', 'Unknown item')} - "
                f"INR {item.get('price', 'N/A')} "
                f"({availability})"
            )

            allergens = item.get("allergens", [])

            if allergens:
                line += " | Allergens: " + ", ".join(allergens)

            lines.append(line)

        if not kitchen_open:
            lines.append(
                "\nThe kitchen is currently closed. "
                "Food orders cannot be placed right now."
            )

        return "\n".join(lines)

    # -------------------------------------------------
    # Approval handling
    # -------------------------------------------------

    def _handle_approval_decision(self, text: str):

        if not self.pending_approval_request_id:
            return None

        approved_words = {
            "approve",
            "approved",
            "yes",
            "confirm",
            "confirmed",
            "accept",
            "accepted"
        }

        rejected_words = {
            "reject",
            "rejected",
            "no",
            "cancel",
            "cancel it",
            "decline",
            "declined"
        }

        if text not in approved_words and text not in rejected_words:
            return (
                "You have a pending approval request. "
                "Please reply APPROVE or REJECT."
            )

        request_id = self.pending_approval_request_id

        request = self.approval_manager.get_request(request_id)

        if request is None:

            self.pending_approval_request_id = None

            return (
                "The pending request could not be found. "
                "Please submit your request again."
            )

        if request.get("guest_id") != self.guest_id:
            return "You are not authorized to approve this request."

        approved = text in approved_words

        self.approval_manager.decide(
            request_id=request_id,
            approved=approved,
            guest_id=self.guest_id
        )

        self.pending_approval_request_id = None

        action = request.get("action", "request")

        if approved:

            if action == "checkout":
                return (
                    "CHECKOUT REQUEST UPDATE\n\n"
                    "Your checkout request has been approved.\n"
                    "The simulated checkout workflow is marked complete.\n\n"
                    "Note: This demo simulates execution. "
                    "It does not physically check you out of the hostel."
                )

            if action == "food_order":
                return (
                    "FOOD ORDER UPDATE\n\n"
                    "Your food order has been approved.\n"
                    "The simulated order workflow is marked complete.\n\n"
                    "Note: This demo simulates execution. "
                    "It does not physically prepare or deliver food."
                )

            return "Your request has been approved."

        if action == "checkout":
            return (
                "CHECKOUT REQUEST UPDATE\n\n"
                "Your checkout request has been rejected.\n"
                "No checkout action was executed."
            )

        if action == "food_order":
            return (
                "FOOD ORDER UPDATE\n\n"
                "Your food order has been rejected.\n"
                "No food order was placed."
            )

        return "Your request has been rejected."

    # -------------------------------------------------
    # Main Orchestrator
    # -------------------------------------------------

    async def ainvoke(self, state):

        messages = state["messages"]

        if not messages:
            raise ValueError("Conversation contains no messages.")

        guest_message = self._get_message_content(
            messages[-1]
        ).strip()

        if not guest_message:

            response = "Please tell me how I can help you."

            return {
                "messages": messages + [
                    AIMessage(content=response)
                ]
            }

        text = guest_message.lower()

        # -------------------------------------------------
        # Handle pending approval before intent routing
        # -------------------------------------------------

        approval_response = self._handle_approval_decision(text)

        if approval_response is not None:

            return {
                "messages": messages + [
                    AIMessage(content=approval_response)
                ]
            }

        # -------------------------------------------------
        # Intent detection
        # -------------------------------------------------

        booking_keywords = [
            "booking",
            "reservation",
            "checkout",
            "check-out",
            "check out",
            "checkin",
            "check-in",
            "check in",
            "stay",
            "room",
            "my date",
            "departure"
        ]

        kitchen_keywords = [
            "food",
            "menu",
            "order",
            "eat",
            "breakfast",
            "lunch",
            "dinner",
            "coffee",
            "sandwich",
            "paneer",
            "dosa",
            "burger",
            "toast",
            "fruit",
            "kitchen",
            "allergen",
            "peanut"
        ]

        booking_request = any(
            self._contains_keyword(text, keyword)
            for keyword in booking_keywords
        )

        kitchen_request = any(
            self._contains_keyword(text, keyword)
            for keyword in kitchen_keywords
        )

        # -------------------------------------------------
        # Checkout action detection
        # -------------------------------------------------

        checkout_action_words = [
            "request checkout",
            "request check out",
            "checkout please",
            "check me out",
            "i want to checkout",
            "i want to check out",
            "i want my checkout",
            "please checkout",
            "please check out",
            "please check me out",
            "please initiate my checkout",
            "initiate my checkout",
            "checkout now",
            "initiate checkout",
            "initiate check out"
        ]

        checkout_action = any(
            self._contains_keyword(text, phrase)
            for phrase in checkout_action_words
        )

        responses = []

        # -------------------------------------------------
        # Booking Specialist
        # -------------------------------------------------

        if booking_request:

            if checkout_action:

                booking_instruction = (
                    "Handle the guest's checkout request.\n"
                    "You MUST use your booking tools.\n"
                    "First retrieve the authenticated guest's booking "
                    "and verify the booking status.\n"
                    "If the guest is eligible to checkout, call "
                    "request_my_checkout.\n"
                    "Never claim checkout has completed. "
                    "The tool only creates a pending approval request.\n"
                    "Do not answer food or kitchen questions.\n\n"
                    f"Guest request: {guest_message}"
                )

            else:

                booking_instruction = (
                    "Handle ONLY the booking-related part of the "
                    "guest request.\n"
                    "Use your tools to retrieve the authenticated "
                    "guest's booking information.\n"
                    "Do not initiate checkout unless the guest "
                    "explicitly requests it.\n"
                    "Never invent booking details.\n"
                    "Do not answer food or kitchen questions.\n\n"
                    f"Guest request: {guest_message}"
                )

            try:

                self._reset_counter(self.booking_counter)

                booking_result = await self.booking_agent.ainvoke(
                    {
                        "messages": [
                            {
                                "role": "user",
                                "content": booking_instruction
                            }
                        ]
                    },
                    config={"recursion_limit": 12}
                )

            except GraphRecursionError:

                response = (
                    "I couldn't complete your booking request because "
                    "the specialist reached its execution limit. "
                    "Please try again with a simpler request."
                )

                return {
                    "messages": messages + [
                        AIMessage(content=response)
                    ]
                }

            if checkout_action:

                checkout_results = self._extract_tool_results(
                    booking_result,
                    {"request_my_checkout"}
                )

                pending_request = next(
                    (
                        item for item in checkout_results
                        if item.get("status") == "pending_approval"
                    ),
                    None
                )

                if pending_request:

                    registered = self.approval_manager.create_request(
                        pending_request
                    )

                    self.pending_approval_request_id = (
                        registered["request_id"]
                    )

                    response = (
                        "CHECKOUT APPROVAL REQUIRED\n\n"
                        "Your checkout request has been submitted "
                        "for approval.\n\n"
                        f"Guest: {registered.get('name', 'Guest')}\n"
                        f"Room: {registered.get('room_number', 'N/A')}\n"
                        f"Request ID: {registered['request_id']}\n\n"
                        "Please reply APPROVE to approve this request "
                        "or REJECT to reject it."
                    )

                    return {
                        "messages": messages + [
                            AIMessage(content=response)
                        ]
                    }

                rejected_request = next(
                    (
                        item for item in checkout_results
                        if item.get("status") in ("rejected", "error")
                    ),
                    None
                )

                if rejected_request:

                    response = (
                        "CHECKOUT REQUEST NOT ACCEPTED\n\n"
                        + rejected_request.get(
                            "reason",
                            "Your checkout request cannot be processed."
                        )
                    )

                    return {
                        "messages": messages + [
                            AIMessage(content=response)
                        ]
                    }

                agent_messages = booking_result.get("messages", [])

                agent_response = next(
                    (
                        self._get_message_content(message)
                        for message in reversed(agent_messages)
                        if isinstance(message, AIMessage)
                        and self._get_message_content(message).strip()
                    ),
                    "Unable to process your checkout request."
                )

                responses.append(agent_response)

            else:

                booking_tool_results = self._extract_tool_results(
                    booking_result,
                    {"get_my_booking"}
                )

                responses.append(
                    self._format_booking(booking_tool_results)
                )

        # -------------------------------------------------
        # Kitchen Specialist
        # -------------------------------------------------

        if kitchen_request:

            order_phrases = [
                "order",
                "i want to have",
                "i would like to have",
                "i would like to order",
                "can i have",
                "please bring",
                "get me"
            ]

            food_order_request = any(
                self._contains_keyword(text, phrase)
                for phrase in order_phrases
            )

            selected_item_id = None
            selected_item_name = None

            if food_order_request:

                # Resolve the food item from the current message
                # or from previous user messages in the conversation.
                selected_item_id, selected_item_name = (
                    self._resolve_food_item_from_history(
                        messages[:-1],
                        guest_message
                    )
                )

                if selected_item_id is None:

                    response = (
                        "Which food item would you like to order? "
                        "Please specify an item from the menu."
                    )

                    return {
                        "messages": messages + [
                            AIMessage(content=response)
                        ]
                    }

                kitchen_instruction = (
                    "The guest is requesting an actual food order.\n"
                    "You MUST call request_my_food_order.\n"
                    f"Item ID: {selected_item_id}\n"
                    "Quantity: 1\n"
                    "Use the authenticated guest context already "
                    "provided to you.\n"
                    "Do not call the menu tool instead of the order tool.\n"
                    "The tool validates kitchen hours, stock "
                    "and guest eligibility.\n"
                    "Never claim the order is completed. "
                    "The tool only creates a pending approval request.\n\n"
                    f"Guest request: {guest_message}"
                )

            else:

                kitchen_instruction = (
                    "The guest is asking about the kitchen or menu.\n"
                    "You MUST use get_kitchen_menu to retrieve the "
                    "actual menu and kitchen status.\n"
                    "Do not place a food order unless the guest "
                    "explicitly requests one.\n"
                    "Do not answer booking or checkout questions.\n"
                    "Do not invent food items, prices, stock "
                    "or serving hours.\n\n"
                    f"Guest request: {guest_message}"
                )

            try:

                self._reset_counter(self.kitchen_counter)

                kitchen_result = await self.kitchen_agent.ainvoke(
                    {
                        "messages": [
                            {
                                "role": "user",
                                "content": kitchen_instruction
                            }
                        ]
                    },
                    config={"recursion_limit": 12}
                )

            except GraphRecursionError:

                response = (
                    "I couldn't complete your kitchen request because "
                    "the specialist reached its execution limit. "
                    "Please try again with a simpler request."
                )

                return {
                    "messages": messages + [
                        AIMessage(content=response)
                    ]
                }

            if food_order_request:

                order_results = self._extract_tool_results(
                    kitchen_result,
                    {"request_my_food_order"}
                )

                pending_order = next(
                    (
                        item for item in order_results
                        if item.get("status") == "pending_approval"
                    ),
                    None
                )

                if pending_order:

                    registered = self.approval_manager.create_request(
                        pending_order
                    )

                    self.pending_approval_request_id = (
                        registered["request_id"]
                    )

                    response = (
                        "FOOD ORDER APPROVAL REQUIRED\n\n"
                        "Your food order has been submitted "
                        "for approval.\n\n"
                        f"Item: {selected_item_name.title() if selected_item_name else 'Unknown item'}\n"
                        f"Quantity: {registered.get('quantity', 1)}\n"
                        f"Total: INR {registered.get('total_price', 'N/A')}\n"
                        f"Room: {registered.get('room_number', 'N/A')}\n"
                        f"Request ID: {registered['request_id']}\n\n"
                        "Please reply APPROVE to approve this order "
                        "or REJECT to reject it."
                    )

                    return {
                        "messages": messages + [
                            AIMessage(content=response)
                        ]
                    }

                rejected_order = next(
                    (
                        item for item in order_results
                        if item.get("status") in ("rejected", "error")
                    ),
                    None
                )

                if rejected_order:

                    response = (
                        "FOOD ORDER NOT ACCEPTED\n\n"
                        + rejected_order.get(
                            "reason",
                            "The food order could not be processed."
                        )
                    )

                    return {
                        "messages": messages + [
                            AIMessage(content=response)
                        ]
                    }

                response = (
                    "I could not submit your food order. "
                    "Please try again."
                )

                return {
                    "messages": messages + [
                        AIMessage(content=response)
                    ]
                }

            else:

                kitchen_tool_results = self._extract_tool_results(
                    kitchen_result,
                    {"get_kitchen_menu"}
                )

                responses.append(
                    self._format_kitchen(kitchen_tool_results)
                )

        # -------------------------------------------------
        # Unsupported requests
        # -------------------------------------------------

        if not booking_request and not kitchen_request:

            response = (
                "Welcome to Sunrise Hostel Concierge!\n\n"
                "I can help you with:\n"
                "- Booking and reservation information\n"
                "- Checkout information and requests\n"
                "- Kitchen menu and availability\n"
                "- Food ordering requests\n\n"
                "I cannot help with requests outside these services."
            )

        else:

            response = "\n\n".join(responses)

        return {
            "messages": messages + [
                AIMessage(content=response)
            ]
        }


# -------------------------------------------------
# Orchestrator factory
# -------------------------------------------------

async def create_hostel_orchestrator(guest_id: str):

    (
        booking_agent,
        kitchen_agent,
        booking_counter,
        kitchen_counter
    ) = await create_specialist_agents(guest_id)

    return HostelOrchestrator(
        guest_id=guest_id,
        booking_agent=booking_agent,
        kitchen_agent=kitchen_agent,
        booking_counter=booking_counter,
        kitchen_counter=kitchen_counter
    )
