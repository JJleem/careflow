from enum import StrEnum


class UserRole(StrEnum):
    customer = "customer"
    counselor = "counselor"
    admin = "admin"


class SubjectRelation(StrEnum):
    self = "self"
    family = "family"


class ServiceType(StrEnum):
    """분석 서비스 종류. 표시용 한글명은 프론트에서 매핑한다."""

    comprehensive_metabolic = "comprehensive_metabolic"  # 종합 대사 분석
    food_intolerance = "food_intolerance"  # 음식물 과민증
    heavy_metal = "heavy_metal"  # 영양중금속 위험도


class ReservationStatus(StrEnum):
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"


class DraftSource(StrEnum):
    manual = "manual"
    llm = "llm"


class BriefingStatus(StrEnum):
    pending = "pending"
    processing = "processing"
    done = "done"
    failed = "failed"
    cancelled = "cancelled"


class WaitlistStatus(StrEnum):
    waiting = "waiting"
    notified = "notified"
    expired = "expired"


class NotificationType(StrEnum):
    confirm = "confirm"
    cancel = "cancel"
    reminder_24h = "reminder_24h"
    reminder_1h = "reminder_1h"
    waitlist = "waitlist"
