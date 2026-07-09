from abc import ABC, abstractmethod

from app.models import Notification


class NotificationChannel(ABC):
    """발송 채널 계약 (NFR-4). 새 채널은 이 인터페이스 구현체 등록만으로 추가되며
    도메인 코드(서비스 레이어)는 변경되지 않는다."""

    @abstractmethod
    def send(self, notification: Notification) -> bool:
        """발송 성공 여부. False면 sent_at이 기록되지 않아 다음 폴링에서 재시도된다."""


class InAppChannel(NotificationChannel):
    """인앱 알림함: 알림 행 자체가 수신함이므로 발송은 항상 성공."""

    def send(self, notification: Notification) -> bool:
        return True


class KakaoAlimtalkChannel(NotificationChannel):
    """확장 지점 (미구현, docs/04 §4.7): 템플릿 사전 승인 + 발신프로필 등록,
    발송 실패 시 SMS 폴백 체인. 계약이 동일하므로 도메인 코드 무변경으로 추가된다."""

    def send(self, notification: Notification) -> bool:
        raise NotImplementedError("알림톡 채널은 실운영 확장 지점입니다")
