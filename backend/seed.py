"""데모 시드 — 3역할 계정, 피검자, 결과지 3종, 상담 슬롯.

멱등: 이미 시드된 DB에서는 아무것도 하지 않으므로 컨테이너 재시작에 안전하다.
슬롯은 실행일 기준 다음 14일의 평일에 생성되어 언제 실행해도 데모가 성립한다.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db import SessionLocal
from app.security import hash_password
from app.models import (
    AvailabilitySlot,
    CounselorProfile,
    ServiceType,
    Subject,
    SubjectRelation,
    TestResult,
    User,
    UserRole,
)

KST = ZoneInfo("Asia/Seoul")
DEMO_PASSWORD = "demo1234"  # 전 계정 공통 — README 데모 시나리오에 명시

SLOT_HOURS = (10, 11, 14, 15, 16)
SLOT_MINUTES = 30
SEED_DAYS = 14

INDICATORS = {
    ServiceType.comprehensive_metabolic: [
        {"name": "공복혈당", "value": 104, "unit": "mg/dL", "range": "70~99",
         "comment": "경계 수준입니다. 정제 탄수화물 섭취를 줄이고 식후 가벼운 활동을 권장합니다."},
        {"name": "HDL 콜레스테롤", "value": 42, "unit": "mg/dL", "range": "60 이상",
         "comment": "다소 낮습니다. 오메가3 지방산과 유산소 운동이 개선에 도움이 됩니다."},
        {"name": "호모시스테인", "value": 13.8, "unit": "µmol/L", "range": "5~12",
         "comment": "상승 소견. 엽산·비타민 B12 보충을 고려해 보세요."},
    ],
    ServiceType.food_intolerance: [
        {"name": "우유(카제인)", "value": 3.2, "unit": "등급(0~4)", "range": "0~1",
         "comment": "높은 반응. 4주 제거 후 재도입 테스트를 권장합니다."},
        {"name": "밀(글루텐)", "value": 2.1, "unit": "등급(0~4)", "range": "0~1",
         "comment": "중등도 반응. 섭취 빈도를 줄이고 증상 일지를 작성해 보세요."},
        {"name": "달걀 흰자", "value": 0.4, "unit": "등급(0~4)", "range": "0~1",
         "comment": "정상 범위입니다."},
    ],
    ServiceType.heavy_metal: [
        {"name": "수은(Hg)", "value": 1.9, "unit": "µg/g", "range": "1.0 미만",
         "comment": "기준 초과. 대형 어류 섭취를 줄이고 셀레늄이 풍부한 식품을 권장합니다."},
        {"name": "납(Pb)", "value": 0.6, "unit": "µg/g", "range": "1.0 미만",
         "comment": "정상 범위입니다."},
        {"name": "아연(Zn)", "value": 58, "unit": "µg/g", "range": "70~120",
         "comment": "부족 소견. 아연은 중금속 배출 효소의 보조 인자로 보충이 필요합니다."},
    ],
}


def seed() -> None:
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)):
            print("seed: 이미 시드된 DB — 건너뜀")
            return

        pw = hash_password(DEMO_PASSWORD)

        admin = User(email="admin@careflow.kr", password_hash=pw,
                     role=UserRole.admin, name="오운영", phone="010-9000-0001")
        co1 = User(email="counselor1@careflow.kr", password_hash=pw,
                   role=UserRole.counselor, name="김민정", phone="010-9000-0002")
        co2 = User(email="counselor2@careflow.kr", password_hash=pw,
                   role=UserRole.counselor, name="정현우", phone="010-9000-0003")
        cu1 = User(email="customer1@careflow.kr", password_hash=pw,
                   role=UserRole.customer, name="이보람", phone="010-1000-0001")
        cu2 = User(email="customer2@careflow.kr", password_hash=pw,
                   role=UserRole.customer, name="박지훈", phone="010-1000-0002")
        db.add_all([admin, co1, co2, cu1, cu2])
        db.flush()

        cp1 = CounselorProfile(user_id=co1.id, specialty="대사·영양")
        cp2 = CounselorProfile(user_id=co2.id, specialty="과민증·중금속")
        # 고객1은 본인 + 가족(모) 피검자 보유 — 가족 결과 상담(P2) 데모용
        s1 = Subject(owner_user_id=cu1.id, name="이보람",
                     birth_date=date(1992, 3, 14), relation=SubjectRelation.self)
        s2 = Subject(owner_user_id=cu1.id, name="김영자",
                     birth_date=date(1965, 8, 2), relation=SubjectRelation.family)
        s3 = Subject(owner_user_id=cu2.id, name="박지훈",
                     birth_date=date(1988, 11, 23), relation=SubjectRelation.self)
        db.add_all([cp1, cp2, s1, s2, s3])
        db.flush()

        today = datetime.now(KST).date()
        results = [
            TestResult(subject_id=s1.id, service_type=ServiceType.comprehensive_metabolic,
                       reported_at=today - timedelta(days=3),
                       indicators=INDICATORS[ServiceType.comprehensive_metabolic]),
            TestResult(subject_id=s2.id, service_type=ServiceType.heavy_metal,
                       reported_at=today - timedelta(days=7),
                       indicators=INDICATORS[ServiceType.heavy_metal]),
            TestResult(subject_id=s3.id, service_type=ServiceType.food_intolerance,
                       reported_at=today - timedelta(days=1),
                       indicators=INDICATORS[ServiceType.food_intolerance]),
        ]
        db.add_all(results)

        slots = []
        for offset in range(1, SEED_DAYS + 1):
            day = today + timedelta(days=offset)
            if day.weekday() >= 5:  # 주말 제외
                continue
            for hour in SLOT_HOURS:
                start = datetime.combine(day, time(hour), tzinfo=KST)
                for cp in (cp1, cp2):
                    slots.append(AvailabilitySlot(
                        counselor_id=cp.id,
                        start_at=start,
                        end_at=start + timedelta(minutes=SLOT_MINUTES),
                    ))
        db.add_all(slots)

        db.commit()
        print(f"seed: 계정 5, 피검자 3, 결과지 {len(results)}, 슬롯 {len(slots)} 생성 완료")


if __name__ == "__main__":
    seed()
