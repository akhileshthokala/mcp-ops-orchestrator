# Native Cloud Validation Plan

This repo is intentionally local-first because MCP stdio servers are easiest to inspect as subprocesses. The next cloud validation step is to preserve the same tool boundaries while moving runtime concerns to managed infrastructure.

## Goal

Validate the orchestration pattern in a sandbox cloud environment without introducing real customer data:

- Containerize the orchestrator and MCP server processes.
- Store mock CRM/ticket data in a managed datastore or controlled object storage.
- Write structured run logs to the platform logging service.
- Keep human approval before any external/customer-facing action.

## GCP-Oriented Smoke Test

For a Google Cloud validation pass:

1. Package the CLI/orchestrator into a container image.
2. Run it as a Cloud Run Job for one synthetic shipment event.
3. Store `ANTHROPIC_API_KEY` in Secret Manager.
4. Send JSONL logs to Cloud Logging.
5. Confirm the run creates a synthetic ticket and stops at the human approval gate.

## Safety Notes

- Keep all CRM and ticket records synthetic.
- Do not connect to employer/customer ticketing, email, or CRM systems from this public repo.
- Do not check in `.env`, logs, credentials, or mutated runtime state.
