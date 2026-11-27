# Architecture & Design Note — Hostel Concierge Multi-Agent System

## Purpose and scope

This prototype demonstrates a guest-facing AI concierge that coordinates two narrowly scoped agents: **Booking** and **Kitchen**. It uses mock hostel data and simulated approval outcomes to demonstrate multi-agent delegation, MCP tool integration, contextual follow-ups and execution guardrails. It is an assignment prototype, not a production property-management or food-ordering system.

## High-level architecture

```text
Guest conversation + guest_id (application context)
                    |
                    v
             HostelOrchestrator
       intent routing | context | approvals
              /              \
             v                v
     Booking Specialist   Kitchen Specialist
       booking tools        kitchen tools
             \                /
              v              v
               MCP client (stdio)
                      |
                      v
             Sunrise Hostel MCP Server
                      |
            JSON mock data (guests,
             menu, kitchen hours)
```

## Component responsibilities

| Component | Responsibility |
|---|---|
| **HostelOrchestrator** | Accepts conversation state, identifies booking and/or kitchen intent, invokes the relevant specialist(s), formats tool results, resolves menu-item references from earlier guest messages, and handles pending approval decisions. |
| **Booking Specialist** | Uses only guest-scoped booking and checkout tools. Retrieves booking information and submits checkout requests. |
| **Kitchen Specialist** | Uses only menu and food-order tools. Reports menu, price, stock, allergen and kitchen-status information, and submits food-order requests. |
| **MCP client/server** | The client discovers the MCP tools and provides them to the application wrappers. The server exposes four tools over stdio and reads the local JSON data files. |
| **Approval manager** | Tracks the pending request and its decision in application memory. Approval/rejection responses are handled by the orchestrator. |

Both specialists are LangGraph ReAct agents using the configured Ollama chat model (`llama3.2:3b`, temperature 0). Each specialist receives a separate allow-listed toolset; the application supplies the guest ID to the wrappers rather than asking the language model or guest to choose an identity.

## Request and approval flow

1. The orchestrator receives the latest guest message and conversation history.
2. It checks for a decision on an outstanding approval before routing a new request.
3. It identifies booking intent, kitchen intent, or both. For a combined request, it can invoke both specialists.
4. A specialist uses its permitted tools. The MCP server validates the guest, booking status, item, quantity, stock and kitchen operating status as applicable.
5. Read-only information is returned to the orchestrator for a guest-facing response. A valid checkout or food-order request returns **pending approval**; it is not executed automatically.
6. The guest replies to approve or reject. The orchestrator checks the pending request and guest context, records the decision, and reports the simulated outcome. Rejection does not execute the requested action.

For contextual food follow-ups, the orchestrator first checks whether the current message names a menu item. If not, it searches previous **guest** messages for a known menu item; it deliberately does not infer the item from assistant menu listings.

## Guardrails and validation

- **Guest scoping:** guest identity is supplied by application context and passed through the specialist wrappers to MCP tools.
- **Tool isolation:** Booking can call only `get_my_booking` and `request_my_checkout`; Kitchen can call only `get_kitchen_menu` and `request_my_food_order`.
- **Server-side checks:** checkout and food ordering require a checked-in guest. Food orders also validate item existence, availability, quantity (1–10) and kitchen opening hours.
- **Approval gate:** checkout and food-order requests remain pending until an explicit guest decision is processed.
- **Bounded execution:** each specialist has an independent maximum of four MCP tool executions per invocation. LangGraph recursion limits provide an additional bound on agent execution.
- **Honest responses:** agents are instructed to use tool results as the source of truth, disclose unavailable information and avoid claiming that a pending or simulated operation has physically completed.

## Data and known limitations

Guest records, menu items and kitchen hours are stored in JSON files. Approval state is in memory, so it is not durable across process restarts. Checkout and food-order completion are simulated; there is no live PMS, payment, inventory or kitchen integration. The repository currently demonstrates the workflow through test/demo modules rather than a production web interface.

## Verification

The test suite covers combined specialist routing, checkout rejection, food-order approval, specialist execution limits, MCP tool-call limits, conversation-history preservation, ambiguous requests, out-of-scope requests and contextual menu follow-ups. All nine test modules passed in the development environment at the time of the assignment documentation.
