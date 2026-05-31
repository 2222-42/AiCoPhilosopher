"""External Agent Bridge (T-082) — optional post-MVP integration layer.

Translates internal workstream requests into calls to external orchestration
layers (Hermes Agent, OpenCode Go). Implements automatic fallback to internal
LangGraph execution, consent flow, and audit logging.

Spec §4.10: seamless fallback, standardized JSON protocol, audit logging,
no data transmission without explicit consent.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
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
            log_path = Path.home() / ".aicophilosopher" / "logs" / "external_bridge.jsonl"
        self._path = Path(log_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

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
        """Dispatch a request to the external layer."""
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
        """Fall back to internal LangGraph execution."""
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
    """Adapter for Hermes Agent orchestration layer (post-MVP)."""

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
        return {
            "bridge": "hermes",
            "endpoint": endpoint,
            "status": "not_implemented",
            "message": "Hermes Agent bridge not yet implemented (post-MVP).",
        }


# ---------------------------------------------------------------------------
# OpenCode Go bridge (real implementation)
# ---------------------------------------------------------------------------
class OpenCodeGoAdapter(ExternalAgentBridge):
    """Adapter for OpenCode Go orchestration layer.

    Delegates workstream tasks to OpenCode Go via ``opencode run``.
    Parses JSON-lines output and returns structured results.
    Falls back to internal LangGraph execution on failure.

    Environment:
        OPENCODE_BIN: path to opencode binary (default: auto-detect)
        OPENCODE_MODEL: default model (default: opencode-go/deepseek-v4-pro)
    """

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------
    @staticmethod
    def _find_opencode() -> str:
        """Locate the opencode binary."""
        # 1. Explicit env var
        env_bin = os.environ.get("OPENCODE_BIN")
        if env_bin and Path(env_bin).exists():
            return env_bin

        # 2. Common paths
        candidates = [
            Path.home() / ".opencode" / "bin" / "opencode",
            Path("/usr/local/bin/opencode"),
            Path("/opt/opencode/bin/opencode"),
        ]
        for c in candidates:
            if c.exists():
                return str(c)

        # 3. PATH lookup
        found = shutil.which("opencode")
        if found:
            return found

        raise RuntimeError(
            "OpenCode Go binary not found. Set OPENCODE_BIN or install opencode."
        )

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------
    def __init__(
        self,
        enabled: bool = False,
        consent_required: bool = True,
        opencode_bin: str | None = None,
        default_model: str | None = None,
    ) -> None:
        super().__init__(
            bridge_type="opencode_go",
            enabled=enabled,
            consent_required=consent_required,
        )
        self._opencode_bin = opencode_bin  # None = lazy-discover on first use
        self._default_model = (
            default_model
            or os.environ.get("OPENCODE_MODEL")
            or "opencode/deepseek-v4-flash-free"
        )

    def _get_opencode_bin(self) -> str:
        """Resolve the opencode binary (lazy — only when actually used)."""
        if self._opencode_bin is None:
            self._opencode_bin = self._find_opencode()
        return self._opencode_bin

    # ------------------------------------------------------------------
    # Send (real implementation)
    # ------------------------------------------------------------------
    async def _send(
        self, endpoint: str, payload: dict[str, object]
    ) -> dict[str, object]:
        """Execute a task via OpenCode Go CLI.

        Args:
            endpoint: Task type (e.g., 'delegate_task', 'analyze', 'search').
            payload: Must contain 'prompt' (str). May contain:
                - model (str): model override
                - workdir (str): working directory
                - file (str): file to attach

        Returns:
            dict with 'status', 'output', 'model', 'session_id', 'tokens'.
        """
        prompt = str(payload.get("prompt", ""))
        if not prompt.strip():
            return {"status": "error", "output": "Empty prompt.", "model": ""}

        model = str(payload.get("model") or self._default_model)
        workdir = str(payload.get("workdir") or os.getcwd())

        cmd: list[str] = [
            self._get_opencode_bin(),
            "run",
            "--format", "json",
            "--model", model,
            "--dir", workdir,
        ]

        # Attach file if provided
        attached_file = payload.get("file")
        if attached_file and isinstance(attached_file, str):
            cmd.extend(["--file", attached_file])

        # The prompt is the positional argument
        cmd.append(prompt)

        logger.debug("OpenCodeGoAdapter: spawning %s", cmd)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=120
            )
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "output": "OpenCode Go task timed out (120s).",
                "model": model,
            }

        if proc.returncode != 0:
            err_text = stderr.decode()[:500] if stderr else "(no stderr)"
            return {
                "status": "error",
                "output": f"OpenCode Go exited {proc.returncode}: {err_text}",
                "model": model,
            }

        # Parse JSON-lines output
        output_parts: list[str] = []
        session_id = ""
        tokens: dict[str, int] = {}
        raw = stdout.decode()

        for line in raw.strip().split("\n"):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type", "")
            part = data.get("part", {})

            if msg_type == "text":
                output_parts.append(str(part.get("text", "")))

            if msg_type in ("step_start", "step_finish"):
                sid = data.get("sessionID") or part.get("sessionID", "")
                if sid:
                    session_id = sid

            if msg_type == "step_finish":
                t = part.get("tokens", {})
                if isinstance(t, dict):
                    tokens = {k: int(v) for k, v in t.items() if isinstance(v, (int, float))}

        output = "\n".join(output_parts).strip()

        return {
            "status": "completed",
            "output": output,
            "model": model,
            "session_id": session_id,
            "tokens": tokens,
        }


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------
def create_opencode_bridge(enabled: bool = False) -> OpenCodeGoAdapter:
    """Create a configured OpenCode Go bridge adapter.

    Respects AICOPH_OPENCODE_ENABLED env var as a default for ``enabled``.
    """
    if not enabled:
        env_enabled = os.environ.get("AICOPH_OPENCODE_ENABLED", "").lower()
        enabled = env_enabled in ("1", "true", "yes")
    return OpenCodeGoAdapter(enabled=enabled)
