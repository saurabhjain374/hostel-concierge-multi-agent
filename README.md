# Hostel Concierge – Multi-Agent AI System

A multi-agent hostel concierge prototype built with Python, LangGraph, LangChain, Ollama and the Model Context Protocol (MCP).

The system accepts guest requests through a guest-facing orchestrator and delegates booking and kitchen operations to separate specialist agents. Business operations are exposed through MCP tools and use local JSON data for this assignment prototype.

## 1. Features

- Retrieve the current guest's booking and checkout information.
- Retrieve the menu, prices, stock availability, allergens and kitchen operating status.
- Handle combined booking and kitchen questions in one request.
- Submit checkout and food-order requests for explicit guest approval.
- Support approval and rejection of pending requests.
- Preserve short-term conversation history and resolve contextual follow-ups such as “Can I order that?”
- Clarify ambiguous requests and decline unsupported requests.
- Isolate Booking and Kitchen specialist tool access.
- Enforce LangGraph recursion limits and independent MCP tool-call limits for each specialist.

## 2. Architecture

```text
                         Guest
                           |
                           v
                  Orchestrator Agent
                  - Intent routing
                  - Conversation context
                  - Approval handling
                  - Execution guardrails
                           |
                 +---------+---------+
                 |                   |
                 v                   v
         Booking Specialist    Kitchen Specialist
                 |                   |
          Booking tools         Kitchen tools
                 |                   |
                 +---------+---------+
                           |
                           v
                       MCP Server
                           |
              +------------+------------+
              |            |            |
              v            v            v
           Guests         Menu     Kitchen hours
            JSON          JSON         JSON
```

### Orchestrator

The orchestrator is the guest-facing entry point. It identifies request intent, delegates to one or both specialists, carries conversation history into follow-up turns, and manages approval responses.

### Booking Specialist

Handles booking lookups and checkout requests. Its application-facing tools are:

- `get_my_booking`
- `request_my_checkout`

### Kitchen Specialist

Handles menu and kitchen-status lookups and food-order requests. Its application-facing tools are:

- `get_kitchen_menu`
- `request_my_food_order`

The specialists receive separate allow-listed toolsets. The orchestrator supplies the guest identity from application context; guests are not asked to provide a guest ID or room number.

## 3. MCP Tools

The MCP server exposes four business tools over stdio:

| MCP tool | Purpose |
|---|---|
| `get_guest_booking` | Retrieve a guest's booking details |
| `request_checkout` | Submit a checkout request for approval |
| `get_menu` | Retrieve menu data and kitchen status |
| `request_food_order` | Validate and submit a food-order request for approval |

The MCP client is initialized by the specialist-agent setup. The client discovers the server tools and wraps them in specialist-specific tools.

## 4. Mock Data

The application uses local JSON files:

| File | Contents |
|---|---|
| `data/guests.json` | Guest IDs, names, room numbers, booking dates and statuses |
| `data/menu.json` | Seven menu items, prices, availability and allergen information |
| `data/kitchen_hours.json` | Operating days, opening and closing times, and timezone |

The sample data includes checked-in, checked-out and not-arrived guests, an out-of-stock item, and a menu item with a peanut allergen.

## 5. Approval and Safety Controls

### Guest-scoped operations

- Guest identity is supplied by the application.
- Specialist tools use that application-provided identity for guest operations.
- Booking and Kitchen tools are separated by allow-list.

### Approval workflow

Checkout and food-order requests are not executed automatically. They are submitted as pending requests and require the guest to respond with:

- `APPROVE` — approve the pending request.
- `REJECT` — reject the pending request.

A rejected request does not execute the corresponding action. The food-order completion path is simulated; it does not physically prepare or deliver food.

### Execution limits

- LangGraph recursion limits provide a safeguard against uncontrolled agent loops.
- Booking and Kitchen each have an independent limit of four MCP tool executions per specialist invocation.
- Specialist counters are reset for a new invocation.

## 6. Conversation Context

The orchestrator preserves the conversation messages supplied to subsequent turns. When a guest refers to a previously mentioned menu item, the current message is checked first, followed by earlier guest messages.

Example:

**Guest:** Is Veg Sandwich available?

**Concierge:** Veg Sandwich is available for INR 120.

**Guest:** Can I order that?

The orchestrator resolves “that” to Veg Sandwich and submits the food-order request for approval.

## 7. Technology Stack

| Technology | Use |
|---|---|
| Python 3.12 | Application language |
| LangGraph | Agent orchestration and execution |
| LangChain | Model and tool integration |
| Ollama | Local model runtime |
| `llama3.2:3b` | Configured chat model |
| MCP Python SDK | MCP server implementation |
| `langchain-mcp-adapters` | MCP client integration |
| JSON | Assignment mock data |
| pytest | Test framework/dependency |

## 8. Prerequisites

- Python 3.12
- [Ollama](https://ollama.com/)
- Git

Pull the chat model used by the agent:

```powershell
ollama pull llama3.2:3b
```

The `nomic-embed-text` model may also be pulled if required by the broader assignment environment:

```powershell
ollama pull nomic-embed-text
```

**Note:** The current specialist implementation configures `llama3.2:3b`. The current agent workflow does not invoke an embedding model.

## 9. Installation

Clone the repository:

```powershell
git clone https://github.com/saurabhjain374/hostel-concierge-multi-agent.git
cd hostel-concierge-multi-agent
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the project dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Confirm that Ollama is running and the model is available:

```powershell
ollama list
```

## 10. Running the Demo

The repository currently provides runnable test/demo modules rather than a separate production web or CLI application entry point.

Run the main combined booking and kitchen scenario:

```powershell
python -m tests.test_orchestrator
```

The MCP server is launched by the MCP client through stdio when the specialist agents are initialized.

## 11. Running the Tests

Run the complete set of test modules:

```powershell
python -m tests.test_orchestrator
python -m tests.test_checkout_rejection
python -m tests.test_food_order_approval
python -m tests.test_execution_limits
python -m tests.test_tool_call_limit
python -m tests.test_conversation_memory
python -m tests.test_ambiguous_requests
python -m tests.test_out_of_scope
python -m tests.test_contextual_followup
```

### Test coverage

| Test module | Coverage |
|---|---|
| `test_orchestrator` | Booking and kitchen coordination in a combined request |
| `test_checkout_rejection` | Checkout rejection and prevention of execution |
| `test_food_order_approval` | Food-order approval flow |
| `test_execution_limits` | Specialist execution/recursion limits |
| `test_tool_call_limit` | Independent MCP tool-call limits |
| `test_conversation_memory` | Conversation-history preservation |
| `test_ambiguous_requests` | Clarification of ambiguous requests |
| `test_out_of_scope` | Declining unsupported requests |
| `test_contextual_followup` | Resolving a food item from previous guest messages |

## 12. Example Scenarios

The test suite exercises scenarios including:

1. Retrieve a guest's booking details.
2. Ask for the checkout date and available breakfast items together.
3. Submit a checkout request and reject it.
4. Submit a food order and approve it.
5. Resolve “Can I order that?” using the earlier menu discussion.
6. Clarify an unspecified food-order request.
7. Decline an unsupported weather request.
8. Enforce specialist execution and MCP tool-call limits.

## 13. Repository Structure

The main project areas are:

```text
hostel-concierge-multi-agent/
├── data/
│   ├── guests.json
│   ├── menu.json
│   └── kitchen_hours.json
├── src/
│   ├── agents/
│   │   └── specialists.py
│   ├── mcp_server/
│   │   └── server.py
│   └── orchestrator/
│       └── orchestrator.py
├── tests/
│   ├── test_orchestrator.py
│   ├── test_checkout_rejection.py
│   ├── test_food_order_approval.py
│   ├── test_execution_limits.py
│   ├── test_tool_call_limit.py
│   ├── test_conversation_memory.py
│   ├── test_ambiguous_requests.py
│   ├── test_out_of_scope.py
│   └── test_contextual_followup.py
└── requirements.txt
```

## 14. Current Limitations

- Business data is stored in local JSON files.
- Approval state is maintained in application memory and is not durable across process restarts.
- Food-order completion is simulated.
- The project does not integrate with a live hotel management system, payment gateway or kitchen ordering platform.
- The current repository provides test/demo workflows, not a production guest-facing web interface.

## 15. Potential Future Enhancements

- Persist guest, booking and approval data in a database.
- Add durable approval state and workflow recovery.
- Build a guest-facing web or mobile chat interface.
- Integrate real hotel management and kitchen systems.
- Add production authentication and authorization.
- Add structured logging, observability and execution tracing.

## Repository

[https://github.com/saurabhjain374/hostel-concierge-multi-agent](https://github.com/saurabhjain374/hostel-concierge-multi-agent)
