"""데모 시드 — 3역할 계정, 피검자, 결과지, 상담 슬롯, 과거 상담 이력, 오늘 예약.

멱등: 이미 시드된 DB에서는 아무것도 하지 않으므로 컨테이너 재시작에 안전하다.
슬롯은 실행일 기준으로 상대 생성되어 언제 실행해도 데모가 성립한다.

검사 스펙은 실제 바이오컴 공개 서비스 기준:
- 종합 대사기능 분석: 소변 유기산(Organic Acids) 검사, mmol/mol creatinine 단위
- 음식물 과민증 분석: 혈액 IgG 반응 등급(0~4)
- 영양 중금속 분석: 모발 미네랄·중금속, µg/g 단위
회사명은 노출하지 않되(시나리오는 CareFlow로 추상화) 검사 도메인의 리얼리티만 반영한다.
"""

import random
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db import SessionLocal
from app.security import hash_password
from app.models import (
    AvailabilitySlot,
    Briefing,
    BriefingStatus,
    ConsultationRecord,
    CounselorProfile,
    DraftSource,
    Notification,
    NotificationType,
    Reservation,
    ReservationStatus,
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

# 서비스별 표시명·검사법은 프론트 lib/labels.ts와 동기화할 것 (SERVICE_TYPE_LABEL / SERVICE_METHOD)
INDICATORS = {
    # 소변 유기산 검사 — 실제 검사는 64종이지만 데모는 6개 대사 영역을 커버하는 10종으로 큐레이션.
    # range는 프론트 파서 호환("a~b"/"x 미만"/"x 이상"). 주의 판정(8-OHdG·퀴놀린산)은
    # 오늘 예약의 사전 문의·AI 브리핑과 한 스토리로 연결되므로 값 변경 금지.
    ServiceType.comprehensive_metabolic: [
        {"name": "구연산 (에너지 생성)", "value": 210, "unit": "mmol/mol Cr", "range": "150~600",
         "comment": "TCA 회로가 원활합니다. 현재 에너지 대사 컨디션을 유지해 주세요."},
        {"name": "피루브산 (에너지 생성)", "value": 55, "unit": "mmol/mol Cr", "range": "30~90",
         "comment": "당 대사에서 에너지로 넘어가는 길목 지표로, 정상 범위입니다."},
        {"name": "8-OHdG (항산화)", "value": 6.4, "unit": "ng/mg Cr", "range": "5.0 미만",
         "comment": "산화 스트레스 상승 소견. 항산화 식품(베리류·녹색 채소)과 오메가3를 권장합니다."},
        {"name": "퀴놀린산 (정신건강·집중력)", "value": 3.7, "unit": "mmol/mol Cr", "range": "3.0 미만",
         "comment": "신경 흥분성 대사물이 다소 높습니다. 마그네슘 보충과 수면 관리가 도움이 됩니다."},
        {"name": "5-HIAA (정신건강·집중력)", "value": 4.2, "unit": "mmol/mol Cr", "range": "2~8",
         "comment": "세로토닌 대사 지표는 정상 범위입니다."},
        {"name": "β-하이드록시부티르산 (체중 조절)", "value": 3.8, "unit": "mmol/mol Cr", "range": "10 미만",
         "comment": "지방 연소(케톤) 대사는 안정적입니다. 급격한 절식 신호는 없습니다."},
        {"name": "아라비노스 (장 건강)", "value": 38, "unit": "mmol/mol Cr", "range": "50 미만",
         "comment": "장내 효모 대사 지표는 정상 범위입니다."},
        {"name": "힙푸르산 (장 건강)", "value": 310, "unit": "mmol/mol Cr", "range": "150~600",
         "comment": "장내 유익균 대사가 원활합니다. 식이섬유 섭취를 유지해 주세요."},
        {"name": "메틸말론산 (신체 방어)", "value": 1.1, "unit": "mmol/mol Cr", "range": "2.0 미만",
         "comment": "비타민 B12 이용 상태는 양호합니다."},
        {"name": "오로트산 (신체 방어)", "value": 0.7, "unit": "mmol/mol Cr", "range": "1.5 미만",
         "comment": "암모니아 해독 부담 지표는 정상 범위입니다."},
    ],
    # 혈액 IgG 음식물 과민증 — 한국인 식품 패널, 0~4 반응 등급
    ServiceType.food_intolerance: [
        {"name": "우유 (카제인)", "value": 3.2, "unit": "등급(0~4)", "range": "0~1",
         "comment": "높은 반응. 4주 제거 후 재도입 테스트를 권장합니다."},
        {"name": "밀 (글루텐)", "value": 2.1, "unit": "등급(0~4)", "range": "0~1",
         "comment": "중등도 반응. 섭취 빈도를 줄이고 증상 일지를 작성해 보세요."},
        {"name": "달걀 흰자", "value": 0.4, "unit": "등급(0~4)", "range": "0~1",
         "comment": "정상 범위입니다."},
        {"name": "대두", "value": 1.6, "unit": "등급(0~4)", "range": "0~1",
         "comment": "경계 반응. 발효 대두식품(된장·청국장) 위주로 소량 섭취를 권장합니다."},
        {"name": "땅콩", "value": 1.3, "unit": "등급(0~4)", "range": "0~1",
         "comment": "경계 반응. 견과류 단백질원은 아몬드·호두로 다변화해 보세요."},
        {"name": "아몬드", "value": 0.6, "unit": "등급(0~4)", "range": "0~1",
         "comment": "정상 범위입니다."},
        {"name": "새우", "value": 0.3, "unit": "등급(0~4)", "range": "0~1",
         "comment": "정상 범위입니다."},
        {"name": "돼지고기", "value": 0.8, "unit": "등급(0~4)", "range": "0~1",
         "comment": "정상 범위입니다."},
        {"name": "고등어", "value": 0.5, "unit": "등급(0~4)", "range": "0~1",
         "comment": "정상 범위입니다."},
        {"name": "토마토", "value": 0.2, "unit": "등급(0~4)", "range": "0~1",
         "comment": "정상 범위입니다."},
    ],
    # 모발 미네랄·중금속 — µg/g. 중금속은 상한, 영양 미네랄은 하한 기준
    ServiceType.heavy_metal: [
        {"name": "수은 (Hg)", "value": 1.9, "unit": "µg/g", "range": "1.0 미만",
         "comment": "기준 초과. 대형 어류 섭취를 줄이고 셀레늄이 풍부한 식품을 권장합니다."},
        {"name": "납 (Pb)", "value": 0.6, "unit": "µg/g", "range": "1.0 미만",
         "comment": "정상 범위입니다."},
        {"name": "카드뮴 (Cd)", "value": 0.05, "unit": "µg/g", "range": "0.15 미만",
         "comment": "정상 범위입니다."},
        {"name": "알루미늄 (Al)", "value": 6.8, "unit": "µg/g", "range": "10 미만",
         "comment": "정상 범위입니다. 제산제·조리기구 유래 노출은 우려 수준이 아닙니다."},
        {"name": "비소 (As)", "value": 0.09, "unit": "µg/g", "range": "0.2 미만",
         "comment": "정상 범위입니다."},
        {"name": "아연 (Zn)", "value": 58, "unit": "µg/g", "range": "70~120",
         "comment": "부족 소견. 아연은 중금속 배출 효소의 보조 인자로 보충이 필요합니다."},
        {"name": "마그네슘 (Mg)", "value": 22, "unit": "µg/g", "range": "30~80",
         "comment": "부족 소견. 근육 이완·수면에 관여하는 미네랄로 견과류·통곡물 섭취를 권장합니다."},
        {"name": "칼슘 (Ca)", "value": 640, "unit": "µg/g", "range": "250~1200",
         "comment": "정상 범위입니다."},
        {"name": "구리 (Cu)", "value": 16, "unit": "µg/g", "range": "10~28",
         "comment": "정상 범위입니다. 아연 보충 시 구리 균형을 함께 살펴보세요."},
        {"name": "셀레늄 (Se)", "value": 0.95, "unit": "µg/g", "range": "0.7~1.4",
         "comment": "정상 범위입니다. 수은 배출을 돕는 미네랄로 현 수준 유지를 권장합니다."},
    ],
}

# 과거 상담 이력 — 관리자 지표(완료율·노쇼율·전환율·관심 제품 순위)가 실감나도록 분포를 심는다.
# (days_ago, status, 관심 제품, 구매 연결, 상담사idx)
PAST_CONSULTS = [
    (25, "completed", ["오메가3", "비타민D"], True, 0),
    (22, "completed", ["프로바이오틱스", "오메가3"], True, 0),
    (18, "completed", ["마그네슘"], False, 1),
    (14, "completed", ["오메가3", "프로바이오틱스", "비타민D"], True, 0),
    (11, "completed", ["밀크씨슬"], False, 1),
    (8, "completed", ["오메가3", "마그네슘"], True, 1),
    (6, "no_show", [], False, 0),
    (3, "cancelled", [], False, 1),
]

PRODUCT_RECS = {
    "오메가3": "오메가3 1일 1000mg, 식후 복용",
    "비타민D": "비타민D 2000IU, 아침 식후",
    "프로바이오틱스": "프로바이오틱스 100억 CFU, 공복",
    "마그네슘": "마그네슘 300mg, 취침 전",
    "밀크씨슬": "밀크씨슬 실리마린 130mg, 식후",
}


def _record_for(products: list[str], purchase_linked: bool) -> ConsultationRecord:
    recs = [PRODUCT_RECS[p] for p in products if p in PRODUCT_RECS]
    summary = (
        "검사 지표를 함께 확인하고 생활습관·영양 보충 방향을 안내함. "
        + ("관심 제품 구매 의사를 확인함." if purchase_linked else "제품은 추후 검토하기로 함.")
    )
    return ConsultationRecord(
        raw_memo="(데모) 상담 메모 원문",
        summary=summary,
        interested_products=products,
        recommendations=recs,
        follow_up="4주 뒤 재검 권유" if products else "특이사항 없음",
        purchase_linked=purchase_linked,
        draft_source=DraftSource.manual,
    )


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
        tr_metabolic = TestResult(
            subject_id=s1.id, service_type=ServiceType.comprehensive_metabolic,
            reported_at=today - timedelta(days=3),
            indicators=INDICATORS[ServiceType.comprehensive_metabolic])
        tr_metal = TestResult(
            subject_id=s2.id, service_type=ServiceType.heavy_metal,
            reported_at=today - timedelta(days=7),
            indicators=INDICATORS[ServiceType.heavy_metal])
        tr_food = TestResult(
            subject_id=s3.id, service_type=ServiceType.food_intolerance,
            reported_at=today - timedelta(days=1),
            indicators=INDICATORS[ServiceType.food_intolerance])
        db.add_all([tr_metabolic, tr_metal, tr_food])
        db.flush()

        # 상담사별 (customer, subject, test_result) 조합 — 과거/오늘 예약이 참조
        cp_list = (cp1, cp2)
        booking_ctx = [
            (cu1, s1, tr_metabolic),
            (cu1, s2, tr_metal),
            (cu2, s3, tr_food),
        ]

        # 1) 미래 상담 슬롯 (예약 화면 데모) — 다음 14일 평일
        slots = []
        for offset in range(1, SEED_DAYS + 1):
            day = today + timedelta(days=offset)
            if day.weekday() >= 5:  # 주말 제외
                continue
            for hour in SLOT_HOURS:
                start = datetime.combine(day, time(hour), tzinfo=KST)
                for cp in cp_list:
                    slots.append(AvailabilitySlot(
                        counselor_id=cp.id, start_at=start,
                        end_at=start + timedelta(minutes=SLOT_MINUTES)))
        db.add_all(slots)

        # 2) 과거 상담 이력 — 각 상담마다 과거 슬롯 1개 + 예약 + (완료 시) 기록
        rng = random.Random(42)
        records = []
        for i, (days_ago, status, products, purchased, cp_idx) in enumerate(PAST_CONSULTS):
            cp = cp_list[cp_idx]
            customer, subject, tr = booking_ctx[i % len(booking_ctx)]
            # 상담은 평일에만 운영 — 주말에 걸리면 직전 평일로 당긴다 (미래 슬롯 생성 규칙과 일치)
            day = today - timedelta(days=days_ago)
            while day.weekday() >= 5:
                day -= timedelta(days=1)
            start = datetime.combine(day, time(rng.choice(SLOT_HOURS)), tzinfo=KST)
            end = start + timedelta(minutes=SLOT_MINUTES)
            slot = AvailabilitySlot(counselor_id=cp.id, start_at=start, end_at=end)
            db.add(slot)
            db.flush()
            r = Reservation(
                slot_id=slot.id, subject_id=subject.id, test_result_id=tr.id,
                customer_id=customer.id, start_at=start, end_at=end,
                status=ReservationStatus[status], confirmed_at=start - timedelta(days=1))
            if status == "completed":
                r.completed_at = end
            elif status == "no_show":
                r.no_show_at = end
            elif status == "cancelled":
                r.cancelled_at = start - timedelta(hours=3)
            db.add(r)
            db.flush()
            if status == "completed":
                rec = _record_for(products, purchased)
                rec.reservation_id = r.id
                records.append(rec)
        db.add_all(records)

        # 3) 오늘 확정 예약 1건 + 완료된 AI 브리핑 — 상담사 '오늘 일정' 데모.
        #    오늘 남은 오후 시각을 쓰되, 현재보다 뒤로 두어 완료/노쇼 처리 전 상태를 보인다.
        now = datetime.now(KST)
        today_hour = 16 if now.hour < 16 else now.hour + 1
        t_start = datetime.combine(today, time(today_hour), tzinfo=KST)
        t_slot = AvailabilitySlot(
            counselor_id=cp1.id, start_at=t_start,
            end_at=t_start + timedelta(minutes=SLOT_MINUTES))
        db.add(t_slot)
        db.flush()
        today_res = Reservation(
            slot_id=t_slot.id, subject_id=s1.id, test_result_id=tr_metabolic.id,
            customer_id=cu1.id, start_at=t_slot.start_at, end_at=t_slot.end_at,
            status=ReservationStatus.confirmed, confirmed_at=now,
            pre_question="산화 스트레스 지표가 높게 나왔는데 어떤 영양제가 도움이 될까요?")
        db.add(today_res)
        db.flush()
        db.add(Briefing(
            reservation_id=today_res.id, status=BriefingStatus.done,
            content=(
                "[사전 브리핑] 종합 대사기능(유기산) 결과 상담\n"
                "- 8-OHdG 6.4 ng/mg Cr (참고 5.0 미만) — 산화 스트레스 상승, 항산화 보충 안내 권장\n"
                "- 퀴놀린산 3.7 (참고 3.0 미만) — 마그네슘·수면 관리\n"
                "- 구연산·아라비노스는 정상 범위\n"
                "고객 사전 문의: \"산화 스트레스 지표가 높은데 어떤 영양제가 도움이 될까요?\" — 이 주제를 우선 다루세요."
            )))

        # 오늘 예약의 알림 — 확정 + 하루 전 리마인더는 이미 발송 시점 도래(알림함 노출).
        # 실제 발송 경로(_create_side_effects+스케줄러)와 동형의 데이터를 심어 데모에서 알림함이 비지 않게 한다.
        when = t_start.strftime("%m월 %d일 %H:%M")
        db.add_all([
            Notification(
                user_id=cu1.id, reservation_id=today_res.id, type=NotificationType.confirm,
                message=f"{when} 상담 예약이 확정되었습니다.",
                scheduled_at=now, sent_at=now),
            Notification(
                user_id=cu1.id, reservation_id=today_res.id, type=NotificationType.reminder_24h,
                message=f"내일 {when} 상담이 예정되어 있습니다.",
                scheduled_at=t_start - timedelta(days=1), sent_at=t_start - timedelta(days=1)),
        ])

        db.commit()
        print(
            f"seed: 계정 5, 피검자 3, 결과지 3, 슬롯 {len(slots)}, "
            f"과거 상담 {len(PAST_CONSULTS)}(기록 {len(records)}), 오늘 예약 1(브리핑 포함) 생성 완료")


if __name__ == "__main__":
    seed()
