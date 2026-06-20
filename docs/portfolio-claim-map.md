# Portfolio Claim Map

This repo supports the MCP and LLM tool-calling part of the enterprise AI assistant story.

## What It Demonstrates

- MCP servers running as separate stdio subprocesses.
- A Claude-driven planning loop that selects tools, executes them, and summarizes the result.
- Tool boundaries for customer lookup, ticket creation, and email drafting.
- Human approval before a customer-facing action.
- Structured JSONL traces for replay, debugging, and auditability.

## How It Complements the RAG Repo

Use this repo next to `enterprise-rag-clinical-guidelines`:

- `enterprise-rag-clinical-guidelines` demonstrates semantic retrieval, vector search, grounded citations, and an MCP retrieval tool surface.
- `mcp-ops-orchestrator` demonstrates multi-tool orchestration, MCP process boundaries, and human-in-the-loop operational controls.

Together, they make the resume claim concrete without overloading one demo with every concern.
