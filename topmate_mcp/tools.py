from __future__ import annotations

from typing import Any

from mcp.server import MCPServer

from topmate_mcp.runtime import Gateway, TenantGatewayRouter


def register_tools(mcp: MCPServer, gateway: Gateway | TenantGatewayRouter) -> None:
    @mcp.tool()
    async def topmate_creator_get() -> dict[str, Any]:
        """Get the authenticated creator profile."""
        return await gateway.read("creator.get", "creator:read")

    @mcp.tool()
    async def topmate_creator_update(changes: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        """Update creator profile fields."""
        return await gateway.write("creator.update", "creator:write", changes, idempotency_key)

    @mcp.tool()
    async def topmate_availability_get() -> dict[str, Any]:
        """Get creator booking availability and timezone."""
        return await gateway.read("availability.get", "availability:read")

    @mcp.tool()
    async def topmate_availability_set(availability: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        """Replace creator availability rules."""
        return await gateway.write("availability.set", "availability:write", availability, idempotency_key)

    @mcp.tool()
    async def topmate_services_list() -> list[dict[str, Any]]:
        """List 1:1 services offered by the creator."""
        return await gateway.read("services.list", "services:read")

    @mcp.tool()
    async def topmate_service_create(title: str, duration_minutes: int, price: float, currency: str = "INR", description: str | None = None, idempotency_key: str = "") -> dict[str, Any]:
        """Create a 1:1 service."""
        return await gateway.write("services.create", "services:write", {"title": title, "duration_minutes": duration_minutes, "price": price, "currency": currency, "description": description, "status": "draft"}, idempotency_key)

    @mcp.tool()
    async def topmate_service_update(service_id: str, changes: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        """Update a 1:1 service."""
        return await gateway.write("services.update", "services:write", {"id": service_id, **changes}, idempotency_key)

    @mcp.tool()
    async def topmate_bookings_list() -> list[dict[str, Any]]:
        """List creator bookings."""
        return await gateway.read("bookings.list", "bookings:read")

    @mcp.tool()
    async def topmate_booking_create(service_id: str, customer_id: str, starts_at: str, customer_timezone: str | None = None, idempotency_key: str = "") -> dict[str, Any]:
        """Create a booking."""
        return await gateway.write("bookings.create", "bookings:write", {"service_id": service_id, "customer_id": customer_id, "starts_at": starts_at, "customer_timezone": customer_timezone}, idempotency_key)

    @mcp.tool()
    async def topmate_booking_reschedule(booking_id: str, starts_at: str, idempotency_key: str) -> dict[str, Any]:
        """Reschedule a booking."""
        return await gateway.write("bookings.reschedule", "bookings:write", {"id": booking_id, "starts_at": starts_at}, idempotency_key)

    @mcp.tool()
    async def topmate_booking_cancel(booking_id: str, reason: str | None, idempotency_key: str) -> dict[str, Any]:
        """Cancel a booking."""
        return await gateway.write("bookings.cancel", "bookings:write", {"id": booking_id, "reason": reason}, idempotency_key)

    @mcp.tool()
    async def topmate_products_list() -> list[dict[str, Any]]:
        """List creator digital products."""
        return await gateway.read("products.list", "products:read")

    @mcp.tool()
    async def topmate_product_create(title: str, price: float, currency: str = "INR", description: str | None = None, delivery_url: str | None = None, idempotency_key: str = "") -> dict[str, Any]:
        """Create a draft digital product."""
        return await gateway.write("products.create", "products:write", {"title": title, "price": price, "currency": currency, "description": description, "delivery_url": delivery_url}, idempotency_key)

    @mcp.tool()
    async def topmate_product_update(product_id: str, changes: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        """Update a digital product."""
        return await gateway.write("products.update", "products:write", {"id": product_id, **changes}, idempotency_key)

    @mcp.tool()
    async def topmate_product_publish(product_id: str, idempotency_key: str) -> dict[str, Any]:
        """Publish a digital product."""
        return await gateway.write("products.publish", "products:write", {"id": product_id}, idempotency_key)

    @mcp.tool()
    async def topmate_events_list() -> list[dict[str, Any]]:
        """List webinars, cohorts, courses and group events."""
        return await gateway.read("events.list", "events:read")

    @mcp.tool()
    async def topmate_event_create(kind: str, title: str, starts_at: str | None, price: float, currency: str = "INR", capacity: int | None = None, description: str | None = None, idempotency_key: str = "") -> dict[str, Any]:
        """Create a webinar, cohort, course or group event draft."""
        if kind not in {"webinar", "cohort", "course", "group_session"}:
            raise ValueError("kind must be webinar, cohort, course, or group_session")
        return await gateway.write("events.create", "events:write", {"kind": kind, "title": title, "starts_at": starts_at, "price": price, "currency": currency, "capacity": capacity, "description": description}, idempotency_key)

    @mcp.tool()
    async def topmate_event_update(event_id: str, changes: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        """Update a webinar, cohort, course or group event."""
        return await gateway.write("events.update", "events:write", {"id": event_id, **changes}, idempotency_key)

    @mcp.tool()
    async def topmate_event_publish(event_id: str, idempotency_key: str) -> dict[str, Any]:
        """Publish a webinar, cohort, course or group event."""
        return await gateway.write("events.publish", "events:write", {"id": event_id}, idempotency_key)

    @mcp.tool()
    async def topmate_packages_list() -> list[dict[str, Any]]:
        """List creator packages/bundles."""
        return await gateway.read("packages.list", "packages:read")

    @mcp.tool()
    async def topmate_package_create(title: str, item_ids: list[str], price: float, currency: str = "INR", idempotency_key: str = "") -> dict[str, Any]:
        """Create a package that bundles services/products/events."""
        return await gateway.write("packages.create", "packages:write", {"title": title, "item_ids": item_ids, "price": price, "currency": currency}, idempotency_key)

    @mcp.tool()
    async def topmate_package_update(package_id: str, changes: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        """Update a package/bundle."""
        return await gateway.write("packages.update", "packages:write", {"id": package_id, **changes}, idempotency_key)

    @mcp.tool()
    async def topmate_messages_list() -> list[dict[str, Any]]:
        """List creator/customer messages."""
        return await gateway.read("messages.list", "messages:read")

    @mcp.tool()
    async def topmate_message_send(customer_id: str, message: str, channel: str = "priority_dm", idempotency_key: str = "") -> dict[str, Any]:
        """Send a creator message or priority DM."""
        return await gateway.write("messages.send", "messages:write", {"customer_id": customer_id, "message": message, "channel": channel}, idempotency_key)

    @mcp.tool()
    async def topmate_customers_list() -> list[dict[str, Any]]:
        """List customers in creator CRM."""
        return await gateway.read("customers.list", "customers:read")

    @mcp.tool()
    async def topmate_customer_get(customer_id: str) -> dict[str, Any]:
        """Get one customer and interaction history."""
        return await gateway.read("customers.get", "customers:read", {"id": customer_id})

    @mcp.tool()
    async def topmate_customer_add_note(customer_id: str, note: str, idempotency_key: str) -> dict[str, Any]:
        """Add an internal CRM note."""
        return await gateway.write("customers.note", "customers:write", {"id": customer_id, "note": note}, idempotency_key)

    @mcp.tool()
    async def topmate_orders_list() -> list[dict[str, Any]]:
        """List creator orders."""
        return await gateway.read("orders.list", "orders:read")

    @mcp.tool()
    async def topmate_order_get(order_id: str) -> dict[str, Any]:
        """Get one order."""
        return await gateway.read("orders.get", "orders:read", {"id": order_id})

    @mcp.tool()
    async def topmate_payments_list() -> list[dict[str, Any]]:
        """List creator payments."""
        return await gateway.read("payments.list", "payments:read")

    @mcp.tool()
    async def topmate_payment_get(payment_id: str) -> dict[str, Any]:
        """Get one payment and refund state."""
        return await gateway.read("payments.get", "payments:read", {"id": payment_id})

    @mcp.tool()
    async def topmate_payment_refund(payment_id: str, amount: float | None, reason: str | None, idempotency_key: str) -> dict[str, Any]:
        """Refund all or part of a payment."""
        return await gateway.write("payments.refund", "payments:refund", {"id": payment_id, "amount": amount, "reason": reason}, idempotency_key)

    @mcp.tool()
    async def topmate_payouts_list() -> list[dict[str, Any]]:
        """List creator payouts and settlement state."""
        return await gateway.read("payouts.list", "payouts:read")

    @mcp.tool()
    async def topmate_coupons_list() -> list[dict[str, Any]]:
        """List creator coupons."""
        return await gateway.read("coupons.list", "coupons:read")

    @mcp.tool()
    async def topmate_coupon_create(code: str, discount_type: str, discount_value: float, applies_to: list[str] | None, idempotency_key: str) -> dict[str, Any]:
        """Create a fixed or percentage discount coupon."""
        if discount_type not in {"fixed", "percent"}:
            raise ValueError("discount_type must be fixed or percent")
        return await gateway.write("coupons.create", "coupons:write", {"code": code.upper(), "discount_type": discount_type, "discount_value": discount_value, "applies_to": applies_to or []}, idempotency_key)

    @mcp.tool()
    async def topmate_coupon_update(coupon_id: str, changes: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        """Update a coupon."""
        return await gateway.write("coupons.update", "coupons:write", {"id": coupon_id, **changes}, idempotency_key)

    @mcp.tool()
    async def topmate_analytics_summary() -> dict[str, Any]:
        """Return bookings, orders, gross revenue and creator product counts."""
        return await gateway.read("analytics.summary", "analytics:read")

    @mcp.tool()
    async def topmate_webhooks_list() -> list[dict[str, Any]]:
        """List configured webhook subscriptions."""
        return await gateway.read("webhooks.list", "webhooks:read")

    @mcp.tool()
    async def topmate_webhook_create(url: str, events: list[str], secret_name: str | None, idempotency_key: str) -> dict[str, Any]:
        """Create a webhook subscription without returning secret values."""
        return await gateway.write("webhooks.create", "webhooks:write", {"url": url, "events": events, "secret_name": secret_name, "active": True}, idempotency_key)

    @mcp.tool()
    async def topmate_webhook_delete(webhook_id: str, idempotency_key: str) -> dict[str, Any]:
        """Delete a webhook subscription."""
        return await gateway.write("webhooks.delete", "webhooks:write", {"id": webhook_id}, idempotency_key)

    @mcp.tool()
    async def topmate_mcp_capabilities() -> dict[str, Any]:
        """Describe provider mode, supported actions and granted scopes."""
        return gateway.describe()

    @mcp.tool()
    async def topmate_audit_log(limit: int = 100) -> list[dict[str, Any]]:
        """Read recent MCP mutation audit entries."""
        return gateway.audit_entries(limit)
