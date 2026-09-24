from __future__ import annotations

from datetime import datetime, timezone
from itertools import count
from typing import Any

from topmate_mcp.providers.base import TopmateProvider, UnsupportedAction
from topmate_mcp.security import TenantContext


class SandboxProvider(TopmateProvider):
    name = "sandbox"
    capabilities = frozenset({
        "creator.get", "creator.update", "availability.get", "availability.set",
        "services.list", "services.create", "services.update",
        "bookings.list", "bookings.create", "bookings.reschedule", "bookings.cancel",
        "products.list", "products.create", "products.update", "products.publish",
        "events.list", "events.create", "events.update", "events.publish",
        "packages.list", "packages.create", "packages.update",
        "messages.list", "messages.send", "customers.list", "customers.get", "customers.note",
        "orders.list", "orders.get", "payments.list", "payments.get", "payments.refund",
        "payouts.list", "coupons.list", "coupons.create", "coupons.update",
        "analytics.summary", "webhooks.list", "webhooks.create", "webhooks.delete",
    })

    def __init__(self) -> None:
        self._seq = count(1001)
        self.creator: dict[str, Any] = {
            "id": "demo_creator", "name": "Demo Creator", "handle": "demo_creator",
            "bio": "Sandbox creator account for Topmate MCP demonstrations.",
            "timezone": "Asia/Kolkata", "currency": "INR",
        }
        self.availability = {
            "timezone": "Asia/Kolkata",
            "weekly": {
                "monday": [["10:00", "18:00"]], "tuesday": [["10:00", "18:00"]],
                "wednesday": [["10:00", "18:00"]], "thursday": [["10:00", "18:00"]],
                "friday": [["10:00", "18:00"]],
            },
        }
        self.services = [{"id": "svc_100", "title": "1:1 Mentoring", "duration_minutes": 30, "price": 999, "currency": "INR", "status": "published"}]
        self.bookings: list[dict[str, Any]] = []
        self.products: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.packages: list[dict[str, Any]] = []
        self.messages: list[dict[str, Any]] = []
        self.customers = [{"id": "cus_100", "name": "Demo Customer", "email": "customer@example.com", "notes": []}]
        self.orders: list[dict[str, Any]] = []
        self.payments: list[dict[str, Any]] = []
        self.payouts: list[dict[str, Any]] = []
        self.coupons: list[dict[str, Any]] = []
        self.webhooks: list[dict[str, Any]] = []

    def _id(self, prefix: str) -> str:
        return f"{prefix}_{next(self._seq)}"

    @staticmethod
    def _utcnow() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _find(rows: list[dict[str, Any]], row_id: str) -> dict[str, Any]:
        for row in rows:
            if row.get("id") == row_id:
                return row
        raise ValueError(f"Unknown id: {row_id}")

    async def call(self, action: str, payload: dict[str, Any], context: TenantContext) -> Any:
        if action not in self.capabilities:
            raise UnsupportedAction(action)

        if action == "creator.get":
            return self.creator.copy()
        if action == "creator.update":
            self.creator.update(payload)
            return self.creator.copy()
        if action == "availability.get":
            return self.availability.copy()
        if action == "availability.set":
            self.availability = payload.copy()
            return self.availability.copy()

        if action.endswith(".list"):
            bucket = {
                "services.list": self.services, "bookings.list": self.bookings,
                "products.list": self.products, "events.list": self.events,
                "packages.list": self.packages, "messages.list": self.messages,
                "customers.list": self.customers, "orders.list": self.orders,
                "payments.list": self.payments, "payouts.list": self.payouts,
                "coupons.list": self.coupons, "webhooks.list": self.webhooks,
            }[action]
            return [row.copy() for row in bucket]

        if action in {"customers.get", "orders.get", "payments.get"}:
            mapping = {"customers.get": self.customers, "orders.get": self.orders, "payments.get": self.payments}
            return self._find(mapping[action], payload["id"]).copy()

        if action in {"services.create", "products.create", "events.create", "packages.create", "bookings.create", "messages.send", "coupons.create", "webhooks.create"}:
            mapping = {
                "services.create": (self.services, "svc"), "products.create": (self.products, "prd"),
                "events.create": (self.events, "evt"), "packages.create": (self.packages, "pkg"),
                "bookings.create": (self.bookings, "bkg"), "messages.send": (self.messages, "msg"),
                "coupons.create": (self.coupons, "cpn"), "webhooks.create": (self.webhooks, "whk"),
            }
            bucket, prefix = mapping[action]
            row = {"id": self._id(prefix), "created_at": self._utcnow(), **payload}
            if action in {"products.create", "events.create", "services.create"}:
                row.setdefault("status", "draft")
            if action == "bookings.create":
                row.setdefault("status", "confirmed")
            bucket.append(row)
            return row.copy()

        if action in {"services.update", "products.update", "events.update", "packages.update", "coupons.update"}:
            mapping = {
                "services.update": self.services, "products.update": self.products,
                "events.update": self.events, "packages.update": self.packages,
                "coupons.update": self.coupons,
            }
            row = self._find(mapping[action], payload.pop("id"))
            row.update(payload)
            row["updated_at"] = self._utcnow()
            return row.copy()

        if action in {"products.publish", "events.publish"}:
            bucket = self.products if action == "products.publish" else self.events
            row = self._find(bucket, payload["id"])
            row["status"] = "published"
            row["published_at"] = self._utcnow()
            return row.copy()

        if action == "bookings.reschedule":
            row = self._find(self.bookings, payload["id"])
            row["starts_at"] = payload["starts_at"]
            row["status"] = "rescheduled"
            row["updated_at"] = self._utcnow()
            return row.copy()
        if action == "bookings.cancel":
            row = self._find(self.bookings, payload["id"])
            row["status"] = "cancelled"
            row["cancel_reason"] = payload.get("reason")
            row["updated_at"] = self._utcnow()
            return row.copy()
        if action == "customers.note":
            row = self._find(self.customers, payload["id"])
            row.setdefault("notes", []).append({"text": payload["note"], "created_at": self._utcnow()})
            return row.copy()
        if action == "payments.refund":
            payment = self._find(self.payments, payload["id"])
            refund = {
                "id": self._id("rfd"), "payment_id": payment["id"],
                "amount": payload.get("amount") if payload.get("amount") is not None else payment.get("amount"),
                "reason": payload.get("reason"), "status": "succeeded", "created_at": self._utcnow(),
            }
            payment.setdefault("refunds", []).append(refund)
            payment["status"] = "refunded"
            return refund
        if action == "webhooks.delete":
            row = self._find(self.webhooks, payload["id"])
            self.webhooks.remove(row)
            return {"deleted": True, "id": payload["id"]}
        if action == "analytics.summary":
            revenue = sum(float(p.get("amount", 0)) for p in self.payments if p.get("status") == "succeeded")
            return {
                "creator_id": context.creator_id, "bookings": len(self.bookings),
                "orders": len(self.orders), "payments": len(self.payments),
                "gross_revenue": revenue, "currency": self.creator.get("currency", "INR"),
                "products": len(self.products), "services": len(self.services),
                "messages": len(self.messages),
            }

        raise UnsupportedAction(action)
