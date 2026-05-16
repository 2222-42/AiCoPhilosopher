"""External Agent Bridge (T-082) — optional post-MVP integration layer.

Translates internal workstream requests into calls to external orchestration
layers (Hermes Agent, OpenCode Go). Implements automatic fallback to internal
LangGraph execution, consent flow, and audit logging.

Spec §4.10: seamless fallback, standardized JSON protocol, audit logging,
no data transmission without explicit consent.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------
class AuditLogger:
    """JSONL audit trail for external bridge interactions."""

    def __init__(self, log_path: str | Path | None = None) -> None:
        if log_path is None:
            log_path = Path("logs") / "external_bridge.jsonl"
        self._path = Path(log_path)

    def log(
        self,
        event: str,
        bridge_type: str,
        details: dict[str, object] | None = None,
    ) -> None:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "bridge_type": bridge_type,
            "details": details or {},
        }
        try:
            with open(self._path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            logger.warning("Failed to write audit log to %s", self._path)


# ---------------------------------------------------------------------------
# Abstract bridge
# ---------------------------------------------------------------------------
class ExternalAgentBridge(ABC):
    """Base class for external orchestration layer adapters.

    Subclasses implement _send() for the specific external protocol.
    The base class handles consent, fallback, and audit logging.
    """

    def __init__(
        self,
        bridge_type: str = "",
        audit_log: AuditLogger | None = None,
        consent_required: bool = True,
        enabled: bool = False,
    ) -> None:
        self.bridge_type = bridge_type or self.__class__.__name__
        self.enabled = enabled
        self.consent_required = consent_required
        self._audit = audit_log or AuditLogger()
        self._consent_granted: dict[str, bool] = {}

    # ------------------------------------------------------------------
    # Consent
    # ------------------------------------------------------------------
    def request_consent(self, scope: str) -> bool:
        """Request user consent for a specific data-sharing scope.

        Returns True if consent is already granted or not required.
        Returns False if consent is denied.
        """
        if not self.consent_required:
            return True
        if self._consent_granted.get(scope, False):
            return True
        self._audit.log("consent_requested", self.bridge_type, {"scope": scope})
        # In MVP, consent must be pre-granted via config.
        # Interactive consent flow deferred to post-MVP.
        logger.info(
            "Consent required for scope '%s' on bridge '%s'. "
            "Grant via grant_consent().",
            scope,
            self.bridge_type,
        )
        return False

    def grant_consent(self, scope: str) -> None:
        """Grant consent for future requests under this scope."""
        self._consent_granted[scope] = True
        self._audit.log("consent_granted", self.bridge_type, {"scope": scope})

    def revoke_consent(self, scope: str) -> None:
        """Revoke previously granted consent."""
        self._consent_granted.pop(scope, None)
        self._audit.log("consent_revoked", self.bridge_type, {"scope": scope})

    # ------------------------------------------------------------------
    # Request dispatch
    # ------------------------------------------------------------------
    async def request(
        self,
        endpoint: str,
        payload: dict[str, object],
        consent_scope: str = "default",
    ) -> dict[str, object]:
        """Dispatch a request to the external layer.

        Checks consent, attempts external call, and falls back to
        internal execution on failure.

        Response schema:
          - success:   {\"status\": \"success\", \"data\": <_send result>}
          - denied:    {\"status\": \"consent_denied\", \"data\": {}, \"error\": ...}
          - fallback:  {\"status\": \"fallback\", \"data\": {}, \"message\": ...}

        Note: On success, ``response[\"data\"]`` contains the raw result from
        ``_send()`` (which may have its own ``status`` field). Consumers
        should check ``response[\"status\"]`` for the overall outcome and
        inspect ``response[\"data\"]`` for bridge-specific payload.

        Args:
            endpoint: Logical endpoint name (e.g., 'delegate_task').
            payload: JSON-serializable payload.
            consent_scope: Scope identifier for consent check.

        Returns:
            Response dict with at least 'status' and 'data' keys.
        """
        if not self.enabled:
            return await self.fallback(
                RuntimeError(f"Bridge '{self.bridge_type}' is disabled")
            )

        if not self.request_consent(consent_scope):
            return {
                "status": "consent_denied",
                "data": {},
                "error": f"Consent not granted for scope '{consent_scope}'",
            }

        self._audit.log(
            "request_started",
            self.bridge_type,
            {"endpoint": endpoint, "scope": consent_scope},
        )

        try:
            result = await self._send(endpoint, payload)
            self._audit.log(
                "request_completed",
                self.bridge_type,
                {"endpoint": endpoint, "status": "success"},
            )
            return {"status": "success", "data": result}
        except (OSError, ConnectionError, TimeoutError, RuntimeError) as exc:
            logger.warning(
                "External bridge '%s' failed on '%s': %s. Falling back.",
                self.bridge_type,
                endpoint,
                exc,
            )
            self._audit.log(
                "request_failed",
                self.bridge_type,
                {"endpoint": endpoint, "error": str(exc)},
            )
            return await self.fallback(exc)

    # ------------------------------------------------------------------
    # Abstract send
    # ------------------------------------------------------------------
    @abstractmethod
    async def _send(
        self, endpoint: str, payload: dict[str, object]
    ) -> dict[str, object]:
        """Send a request to the external service. Implemented by subclasses."""
        ...

    # ------------------------------------------------------------------
    # Fallback to internal execution
    # ------------------------------------------------------------------
    async def fallback(self, error: Exception) -> dict[str, object]:
        """Fall back to internal LangGraph execution.

        Subclasses can override to provide bridge-specific fallback logic.
        The default implementation returns a graceful-degradation response.
        """
        logger.info(
            "Falling back to internal execution for bridge '%s': %s",
            self.bridge_type,
            error,
        )
        return {
            "status": "fallback",
            "data": {},
            "message": (
                f"External bridge '{self.bridge_type}' unavailable. "
                f"Request handled internally via LangGraph fallback."
            ),
            "error": str(error),
        }


# ---------------------------------------------------------------------------
# Hermes Agent bridge (skeleton)
# ---------------------------------------------------------------------------
class HermesAdapter(ExternalAgentBridge):
    """Adapter for Hermes Agent orchestration layer (post-MVP).

    Translates internal workstream requests to Hermes Agent delegate_task calls.
    Falls back to internal LangGraph execution on failure.
    """

    def __init__(
        self,
        enabled: bool = False,
        consent_required: bool = True,
    ) -> None:
        super().__init__(
            bridge_type="hermes",
            enabled=enabled,
            consent_required=consent_required,
        )

    async def _send(
        self, endpoint: str, payload: dict[str, object]
    ) -> dict[str, object]:
        """Send to Hermes Agent. Skeleton — full impl deferred to Phase 6."""
        # Placeholder: in production, this would call the Hermes Agent API
        return {
            "bridge": "hermes",
            "endpoint": endpoint,
            "status": "not_implemented",
            "message": "Hermes Agent bridge not yet implemented (post-MVP).",
        }


# ---------------------------------------------------------------------------
# OpenCode Go bridge (skeleton)
# ---------------------------------------------------------------------------
class OpenCodeGoAdapter(ExternalAgentBridge):
    """Adapter for OpenCode Go orchestration layer (post-MVP).

    Translates internal workstream requests to OpenCode Go CLI calls.
    Falls back to internal LangGraph execution on failure.
    """

    def __init__(
        self,
        enabled: bool = False,
        consent_required: bool = True,
    ) -> None:
        super().__init__(
            bridge_type="opencode_go",
            enabled=enabled,
            consent_required=consent_required,
        )

    async def _send(
        self, endpoint: str, payload: dict[str, object]
    ) -> dict[str, object]:
        """Send to OpenCode Go. Skeleton — full impl deferred to Phase 6."""
        return {
            "bridge": "opencode_go",
            "endpoint": endpoint,
            "status": "not_implemented",
            "message": "OpenCode Go bridge not yet implemented (post-MVP).",
        }
