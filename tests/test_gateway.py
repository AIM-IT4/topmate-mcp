import asyncio

from topmate_mcp.providers.sandbox import SandboxProvider
from topmate_mcp.runtime import Gateway
from topmate_mcp.security import PermissionDenied, TenantContext


def make_gateway(scopes):
    return Gateway(SandboxProvider(), TenantContext("creator_1", frozenset(scopes)), 1000)


def test_service_create_is_idempotent():
    gateway = make_gateway({"services:write"})

    async def run():
        first = await gateway.write("services.create", "services:write", {"title": "Quant Mentoring", "duration_minutes": 30, "price": 999}, "idem-12345678")
        second = await gateway.write("services.create", "services:write", {"title": "Quant Mentoring", "duration_minutes": 30, "price": 999}, "idem-12345678")
        assert first["idempotent_replay"] is False
        assert second["idempotent_replay"] is True
        assert second["result"]["id"] == first["result"]["id"]

    asyncio.run(run())


def test_scope_is_enforced():
    gateway = make_gateway({"services:read"})

    async def run():
        try:
            await gateway.write("services.create", "services:write", {"title": "Blocked", "duration_minutes": 30, "price": 1}, "idem-12345678")
        except PermissionDenied:
            return
        raise AssertionError("Expected PermissionDenied")

    asyncio.run(run())


def test_booking_lifecycle_and_audit():
    gateway = make_gateway({"bookings:write", "audit:read"})

    async def run():
        created = await gateway.write("bookings.create", "bookings:write", {"service_id": "svc_100", "customer_id": "cus_100", "starts_at": "2026-10-01T10:00:00+05:30"}, "idem-create-1234")
        booking_id = created["result"]["id"]
        rescheduled = await gateway.write("bookings.reschedule", "bookings:write", {"id": booking_id, "starts_at": "2026-10-01T11:00:00+05:30"}, "idem-move-123456")
        assert rescheduled["result"]["status"] == "rescheduled"
        cancelled = await gateway.write("bookings.cancel", "bookings:write", {"id": booking_id, "reason": "customer request"}, "idem-cancel-1234")
        assert cancelled["result"]["status"] == "cancelled"
        assert len(gateway.audit.list()) == 3

    asyncio.run(run())
