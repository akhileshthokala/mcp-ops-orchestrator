"""
Test suite for MCP servers.

Tests the core tool logic directly without spinning up subprocess servers.
"""
import json
import tempfile
from pathlib import Path

import pytest

# We import the tool functions directly for unit testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_servers.customer_lookup import lookup_customer
from mcp_servers.ticket_create import create_ticket


class TestCustomerLookup:
    """Test the customer_lookup tool."""

    def test_lookup_by_exact_id(self):
        """Lookup a customer by exact ID."""
        result = lookup_customer("CUST-001")
        assert result["id"] == "CUST-001"
        assert result["name"] == "Acme Corp"
        assert result["tier"] == "enterprise"

    def test_lookup_by_partial_name(self):
        """Lookup a customer by partial name (case-insensitive)."""
        result = lookup_customer("acme")
        assert result["id"] == "CUST-001"
        assert result["name"] == "Acme Corp"

    def test_lookup_not_found(self):
        """Lookup fails gracefully when customer not found."""
        result = lookup_customer("NonexistentCorp")
        assert "error" in result
        assert "No customer found" in result["error"]

    def test_lookup_whitespace_handling(self):
        """Lookup handles whitespace correctly."""
        result = lookup_customer("  acme  ")
        assert result["id"] == "CUST-001"
        assert result["name"] == "Acme Corp"

    def test_lookup_case_insensitive(self):
        """Lookup is case-insensitive."""
        result = lookup_customer("GLOBEX")
        assert result["id"] == "CUST-002"
        assert result["name"] == "Globex Industries"


class TestTicketCreate:
    """Test the ticket_create tool."""

    def setup_method(self):
        """Set up a temporary tickets file for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tickets_path = Path(self.temp_dir.name) / "tickets.json"
        self.tickets_path.write_text(json.dumps({"tickets": []}))

        # Monkey-patch the TICKETS_PATH in the module
        import mcp_servers.ticket_create as tc
        self.orig_path = tc.TICKETS_PATH
        tc.TICKETS_PATH = self.tickets_path

    def teardown_method(self):
        """Clean up temporary files."""
        import mcp_servers.ticket_create as tc
        tc.TICKETS_PATH = self.orig_path
        self.temp_dir.cleanup()

    def test_create_ticket_success(self):
        """Create a ticket successfully."""
        result = create_ticket(
            customer_id="CUST-001",
            subject="Delayed shipment",
            body="SH-1042 is 48h delayed",
            priority="high",
        )
        assert result["ticket_id"].startswith("TKT-")
        assert result["customer_id"] == "CUST-001"
        assert result["status"] == "open"
        assert result["priority"] == "high"

    def test_create_ticket_default_priority(self):
        """Create a ticket with default priority."""
        result = create_ticket(
            customer_id="CUST-002",
            subject="Issue",
            body="Description",
        )
        assert result["priority"] == "normal"

    def test_create_ticket_invalid_priority(self):
        """Reject invalid priority."""
        result = create_ticket(
            customer_id="CUST-001",
            subject="Issue",
            body="Description",
            priority="ultra-urgent",
        )
        assert "error" in result
        assert "Invalid priority" in result["error"]

    def test_create_ticket_persists(self):
        """Ticket is persisted to disk."""
        create_ticket(
            customer_id="CUST-001",
            subject="Test",
            body="Body",
        )
        data = json.loads(self.tickets_path.read_text())
        assert len(data["tickets"]) == 1
        assert data["tickets"][0]["customer_id"] == "CUST-001"

    def test_create_multiple_tickets(self):
        """Multiple tickets can be created."""
        create_ticket(customer_id="CUST-001", subject="Issue 1", body="Body 1")
        create_ticket(customer_id="CUST-002", subject="Issue 2", body="Body 2")
        data = json.loads(self.tickets_path.read_text())
        assert len(data["tickets"]) == 2
