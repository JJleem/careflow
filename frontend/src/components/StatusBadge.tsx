import type { components } from '../api/schema'
import { cn } from '@/lib/utils'

type ReservationStatus = components['schemas']['ReservationStatus']

// 05 §5.1 시맨틱 매핑 고정: confirmed=info, completed=success, no_show=warning, cancelled=neutral.
// 색+텍스트 병행 표기 (05 §5.5-3)
const STATUS_META: Record<ReservationStatus, { label: string; className: string }> = {
  confirmed: { label: '예약 확정', className: 'bg-primary-soft text-primary' },
  completed: { label: '상담 완료', className: 'bg-primary text-primary-foreground' },
  no_show: { label: '노쇼', className: 'bg-warning/10 text-warning' },
  cancelled: { label: '취소됨', className: 'bg-muted text-muted-foreground' },
}

// "노쇼"는 운영자 내부 용어 — 고객 화면에서는 낙인 없이 중립적으로 표현한다.
// (상담사·관리자 화면은 지표 용어 그대로 유지)
const CUSTOMER_LABEL: Partial<Record<ReservationStatus, string>> = {
  no_show: '상담 미진행',
}

export default function StatusBadge({
  status,
  audience = 'staff',
  className,
}: {
  status: ReservationStatus
  audience?: 'staff' | 'customer'
  className?: string
}) {
  const meta = STATUS_META[status]
  const label = (audience === 'customer' && CUSTOMER_LABEL[status]) || meta.label
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-pill px-2.5 py-0.5 text-caption font-semibold',
        meta.className,
        className,
      )}
    >
      {label}
    </span>
  )
}
