"""External bridge skeleton. Post-MVP."""


class ExternalAgentBridge:
    def __init__(self, bridge_type: str = "") -> None:
        self.bridge_type = bridge_type
        self.enabled = False

    async def request(self, endpoint: str, payload: dict[str, object]) -> dict[str, object]:
        raise NotImplementedError

    async def fallback(self, error: Exception) -> dict[str, object]:
        raise NotImplementedError
