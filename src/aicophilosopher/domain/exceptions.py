class AICoPhilosopherError(Exception):
    pass


class WorkstreamError(AICoPhilosopherError):
    pass


class ReviewDeadlockError(AICoPhilosopherError):
    def __init__(self, workstream_id: str, round_number: int, message: str = ""):
        self.workstream_id = workstream_id
        self.round_number = round_number
        super().__init__(message or f"Review deadlock in workstream {workstream_id} at round {round_number}")


class IncommensurabilityError(AICoPhilosopherError):
    pass


class ExternalLayerError(AICoPhilosopherError):
    pass


class ValidationError(AICoPhilosopherError):
    pass


class ConfigurationError(AICoPhilosopherError):
    pass
