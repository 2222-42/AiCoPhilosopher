from enum import StrEnum


class WorkstreamType(StrEnum):
    LITERATURE_SEARCH = "literature_search"
    CONCEPT_ANALYSIS = "concept_analysis"
    CROSS_TRADITIONAL_COMPARISON = "cross_traditional_comparison"
    ARGUMENTATION = "argumentation"
    CRITICAL_REVIEW = "critical_review"
    PHENOMENOLOGICAL_DESCRIPTION = "phenomenological_description"
    ETHICAL_ANALYSIS = "ethical_analysis"
    SYNTHESIS = "synthesis"


class WorkstreamStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STALLED = "stalled"


class HypothesisStrength(StrEnum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    REFUTED = "refuted"
    UNDERDETERMINED = "underdetermined"


class Origin(StrEnum):
    USER = "user"
    AI = "ai"
    JOINT = "joint"
    CROSS_TRADITION_SYNTHESIS = "cross_tradition_synthesis"


class HypothesisStatus(StrEnum):
    ACTIVE = "active"
    ABANDONED = "abandoned"
    REFINED = "refined"
    REFUTED = "refuted"


class ReviewStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    UNDER_REVIEW = "under_review"
    CONTESTED = "contested"
    ACCEPTED_WITH_RESERVATIONS = "accepted_with_reservations"
    REJECTED = "rejected"


class DialecticalMoveType(StrEnum):
    ARGUMENT = "argument"
    REFUTATION = "refutation"
    REVISION = "revision"
    ABANDONMENT = "abandonment"
    CLARIFICATION = "clarification"
    SYNTHESIS = "synthesis"


class MessageType(StrEnum):
    STATUS_UPDATE = "status_update"
    DELEGATION_REQUEST = "delegation_request"
    DELEGATION_RESPONSE = "delegation_response"
    STEERING_COMMAND = "steering_command"
    STEERING_ACK = "steering_ack"
    HELP_REQUEST = "help_request"
    HELP_RESPONSE = "help_response"
    REVIEW_REQUEST = "review_request"
    REVIEW_RESPONSE = "review_response"
    RESULT_DELIVERY = "result_delivery"
    ERROR_NOTIFICATION = "error_notification"
    USER_NOTIFICATION = "user_notification"


class ArtifactType(StrEnum):
    PDF = "pdf"
    MARKDOWN = "markdown"
    BIBTEX = "bibtex"
    CODE = "code"
    IMAGE = "image"
    JSON = "json"
    OTHER = "other"


class ReviewerVerdictStatus(StrEnum):
    APPROVED = "approved"
    APPROVED_WITH_RESERVATIONS = "approved_with_reservations"
    REJECTED = "rejected"
    ABSTAINED = "abstained"


class ReviewRoundStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    APPROVED_WITH_RESERVATIONS = "approved_with_reservations"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class ProjectStatus(StrEnum):
    CREATED = "created"
    CLARIFYING = "clarifying"
    ACTIVE = "active"
    ARCHIVED = "archived"
