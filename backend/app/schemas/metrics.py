from datetime import date

from pydantic import BaseModel


class ProductCount(BaseModel):
    product: str
    count: int


class MetricsResponse(BaseModel):
    """관리자 지표 응답 (docs/04 §4.4). 비율은 분모 0(해당 기간 0건)이면 null —
    0%(실제 0건 처리)와 '계산 불가'를 구분한다."""

    date_from: date
    date_to: date
    total_reservations: int
    completed: int
    cancelled: int
    no_show: int
    confirmed_upcoming: int
    completion_rate: float | None
    no_show_rate: float | None
    conversion_rate: float | None
    top_interested_products: list[ProductCount]
