import type { components } from '../api/schema'

type ServiceType = components['schemas']['ServiceType']
type SubjectRelation = components['schemas']['SubjectRelation']
type NotificationType = components['schemas']['NotificationType']

// 백엔드는 enum 코드만 주고 표시용 한글명은 프론트가 매핑한다 (schema ServiceType 주석)
export const SERVICE_TYPE_LABEL: Record<ServiceType, string> = {
  comprehensive_metabolic: '종합 대사체 분석',
  food_intolerance: '음식물 과민반응 검사',
  heavy_metal: '중금속 검사',
}

export const RELATION_LABEL: Record<SubjectRelation, string> = {
  self: '본인',
  family: '가족',
}

export const NOTIFICATION_LABEL: Record<NotificationType, string> = {
  confirm: '예약 확정',
  cancel: '예약 취소',
  reminder_24h: '상담 하루 전',
  reminder_1h: '상담 1시간 전',
  waitlist: '대기 예약 확정',
}

/** 지표 정상 범위 판정 — range 문자열("70~99", "1.0 미만", "60 이상")을 해석.
 *  해석 불가하면 null(판정 표시 생략). 표시용 판정일 뿐 의학적 판단은 결과지 comment를 따른다. */
export function isOutOfRange(value: number, range: string): boolean | null {
  const between = range.match(/^([\d.]+)\s*~\s*([\d.]+)$/)
  if (between) return value < Number(between[1]) || value > Number(between[2])
  const below = range.match(/^([\d.]+)\s*미만$/)
  if (below) return value >= Number(below[1])
  const above = range.match(/^([\d.]+)\s*이상$/)
  if (above) return value < Number(above[1])
  return null
}
