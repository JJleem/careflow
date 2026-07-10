import { useMemo, useState } from 'react'
import { useCreateSlot, useDeleteSlot, useMySlots } from '../../api/queries/counselor'
import { detailMessage } from '../../api/error'
import { formatTime, toDateParam, upcomingDays } from '../../lib/datetime'
import ErrorState from '../../components/ErrorState'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

// 30분 슬롯 (백엔드 SLOT_MINUTES=30), 업무 시간 09:00–18:00 KST
const HOURS = Array.from({ length: 18 }, (_, i) => {
  const h = 9 + Math.floor(i / 2)
  const m = i % 2 === 0 ? '00' : '30'
  return `${String(h).padStart(2, '0')}:${m}`
})

export default function SlotsPage() {
  const days = useMemo(() => upcomingDays(14), [])
  const [date, setDate] = useState(() => toDateParam(new Date()))
  const slots = useMySlots(days[0].value, days[13].value)
  const createSlot = useCreateSlot()
  const deleteSlot = useDeleteSlot()

  const daySlots = new Map(
    (slots.data ?? [])
      .filter((s) => toDateParam(new Date(s.start_at)) === date)
      .map((s) => [formatTime(s.start_at), s]),
  )
  const countOf = (d: string) =>
    (slots.data ?? []).filter((s) => toDateParam(new Date(s.start_at)) === d).length

  const mutationError = createSlot.error ?? deleteSlot.error

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-1">
        <h1 className="text-title-md">슬롯 관리</h1>
        <p className="text-caption text-text-secondary">
          비어 있는 시간을 누르면 열리고, 열린 슬롯을 누르면 닫혀요. 예약이 잡힌 슬롯은 닫을 수
          없어요.
        </p>
      </div>

      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
        {days.map((d) => (
          <button
            key={d.value}
            type="button"
            onClick={() => {
              setDate(d.value)
              createSlot.reset()
              deleteSlot.reset()
            }}
            className={cn(
              'flex w-14 shrink-0 flex-col items-center gap-0.5 rounded-control py-2.5 transition-colors',
              date === d.value
                ? 'bg-primary font-semibold text-primary-foreground'
                : 'bg-card text-text shadow-card',
            )}
          >
            <span className={cn('text-caption', date === d.value ? 'text-white/70' : 'text-text-secondary')}>
              {d.weekday}
            </span>
            <span className="text-body font-semibold tabular-nums">{d.day}</span>
            <span className={cn('text-[11px] tabular-nums', date === d.value ? 'text-white/70' : 'text-text-secondary')}>
              {countOf(d.value)}칸
            </span>
          </button>
        ))}
      </div>

      {slots.isPending ? (
        <Skeleton className="h-64 rounded-card" />
      ) : slots.isError ? (
        <ErrorState onRetry={() => slots.refetch()} />
      ) : (
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
          {HOURS.map((hhmm) => {
            const slot = daySlots.get(hhmm)
            const reserved = slot?.has_active_reservation
            // 지난 시각은 슬롯을 열 수 없다(백엔드가 과거 시각 거부) — 비활성 처리
            const past = new Date(`${date}T${hhmm}:00+09:00`).getTime() <= Date.now()
            const locked = reserved || (past && !slot)
            return (
              <button
                key={hhmm}
                type="button"
                disabled={locked || createSlot.isPending || deleteSlot.isPending}
                onClick={() => {
                  createSlot.reset()
                  deleteSlot.reset()
                  if (slot) deleteSlot.mutate(slot.id)
                  else createSlot.mutate(`${date}T${hhmm}:00+09:00`)
                }}
                className={cn(
                  'flex flex-col items-center rounded-control py-2.5 transition-colors disabled:opacity-60',
                  reserved
                    ? 'bg-primary-soft text-primary'
                    : slot
                      ? 'bg-primary font-semibold text-primary-foreground'
                      : 'bg-card text-text-secondary shadow-card',
                )}
              >
                <span className="text-body font-semibold tabular-nums">{hhmm}</span>
                <span className={cn('text-caption', slot && !reserved ? 'text-white/70' : '')}>
                  {reserved ? '예약됨' : slot ? '열림' : past ? '지난 시간' : '닫힘'}
                </span>
              </button>
            )
          })}
        </div>
      )}

      {mutationError && (
        <p role="alert" className="text-caption text-danger">
          {detailMessage(mutationError, '처리하지 못했어요. 잠시 후 다시 시도해 주세요.')}
        </p>
      )}
    </div>
  )
}
