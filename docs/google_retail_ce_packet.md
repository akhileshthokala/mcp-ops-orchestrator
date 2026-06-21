# Google Retail CE Reviewer Packet

## One-Sentence Read

This repo demonstrates a customer-facing operations automation pattern: an agent coordinates isolated tools, records every step, and requires human approval before customer-visible communication.

## Why It Fits A Platform CE Conversation

- **Application modernization:** legacy operational steps become explicit tools with narrow contracts.
- **Cloud-native architecture:** the local subprocess pattern maps to Cloud Run services, GKE workloads, or private service connectors.
- **Retail/logistics relevance:** shipment, fulfillment, and customer exception workflows are adjacent to retail peak-season operations, BOPIS, returns, and inventory promises.
- **Security posture:** approval gates, scoped tools, structured traces, and secret-based provider config are first-class design choices.
- **Sales engineering motion:** the project is easy to demo, easy to scope as a pilot, and easy to turn into a delivery plan.

## Suggested Demo Narrative

1. Start with the customer problem: exception handling is spread across CRM, ticketing, and account communication.
2. Show how the agent uses only the tools it is given: lookup, ticket create, email draft.
3. Pause on the human approval step and explain why the irreversible action is separated from the draft.
4. Open `logs/run.jsonl` to show traceability, latency, and review decisions.
5. Map the pilot to Google Cloud: Pub/Sub or Eventarc ingestion, Cloud Run/GKE for tool servers, Secret Manager for credentials, Cloud Logging for traces, BigQuery for analytics, IAM for scoped access.

## What To Be Honest About

- It is not connected to real customer systems.
- The current orchestration model is Claude; a Google Cloud version would use Gemini/Vertex AI function calling or preserve MCP behind service boundaries.
- Approval currently marks a draft as ready for sending; it does not send real email.
- Unit tests cover deterministic tool behavior. The next engineering step is HITL metadata coverage plus an integration smoke test for the orchestrator loop.

## Highest-Leverage Next Steps

1. Add tests for HITL action metadata and the orchestrator loop.
2. Add a `send_email` MCP tool that is only callable after approval.
3. Add a Cloud Run deployment doc with service-account and Secret Manager boundaries.
4. Add a retail-specific event sample: delayed BOPIS pickup, split shipment, or return exception.
