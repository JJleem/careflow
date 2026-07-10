import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMyReservations, useTransitionReservation } from '../../api/queries/reservations'
import { useBriefings } from '../../api/queries/counselor'
import { useTestResults } from '../../api/queries/results'
import { detailMessage } from '../../api/error'
import { SERVICE_TYPE_LABEL } from '../../lib/labels'
import { formatDate, formatTime, toDateParam } from '../../lib/datetime'
import EmptyState from '../../components/EmptyState'
import ErrorState from '../../components/ErrorState'
import StatusBadge from '../../components/StatusBadge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'

type Action = { id: number; status: 'completed' | 'no_show' }

const ACTION_LABEL = { completed: '완료 처리', no_show: '노쇼 처리' } as const

export default function TodayPage() {
  const reservations = useMyReservations()
  const transition = useTransitionReservation()
  const [action, setAction] = useState<Action | null>(null)

  const today = toDateParam(new Date())
  const todays = (reservations.data ?? [])
    .filter((r) => toDateParam(new Date(r.start_at)) === today)
    .sort((a, b) => a.start_at.localeCompare(b.start_at))

  const resultQueries = useTestResults([...new Set(todays.map((r) => r.test_result_id))])
  const serviceOf = (testResultId: number) => {
    const found = resultQueries.find((q) => q.data?.id === testResultId)?.data
    return found ? SERVICE_TYPE_LABEL[found.service_type] : null
  }

  const briefings = useBriefings(todays.map((r) => r.id))

  if (reservations.isPending) {
    return (
      <div className="flex flex-col gap-3">
        <h1 className="text-title-md">오늘 일정</h1>
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-32 rounded-card" />
        ))}
      </div>
    )
  }
  if (reservations.isError) return <ErrorState onRetry={() => reservations.refetch()} />

  const done = todays.filter((r) => r.status === 'completed').length
  const target = todays.find((r) => r.id === action?.id)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-baseline justify-between">
        <h1 className="text-title-md">오늘 일정</h1>
        <p className="text-caption text-text-secondary">
          {formatDate(new Date().toISOString())} · {todays.length}건 중 {done}건 완료
        </p>
      </div>

      {todays.length === 0 ? (
        <EmptyState
          title="오늘 예약된 상담이 없어요"
          description="슬롯 관리에서 상담 가능 시간을 열 수 있어요"
          action={
            <Button asChild variant="secondary" size="sm">
              <Link to="/work/slots">슬롯 관리</Link>
            </Button>
          }
        />
      ) : (
        <ul className="flex flex-col gap-3">
          {todays.map((r, i) => {
            const briefing = briefings[i]?.data
            return (
              <li key={r.id} className="flex flex-col gap-3 rounded-card bg-card p-5 shadow-card">
                <div className="flex items-center gap-3">
                  <span className="text-title-sm font-bold tabular-nums">
                    {formatTime(r.start_at)}–{formatTime(r.end_at)}
                  </span>
                  <StatusBadge status={r.status} />
                  <span className="ml-auto text-caption text-text-secondary">
                    {serviceOf(r.test_result_id) ?? `결과지 #${r.test_result_id}`}
                  </span>
                </div>

                {r.pre_question && (
                  <p className="rounded-chip bg-surface px-3 py-2 text-caption text-text-secondary">
                    사전 문의 — {r.pre_question}
                  </p>
                )}

                {briefing &&
                  (briefing.status === 'done' && briefing.content ? (
                    <div className="flex flex-col gap-1 rounded-chip bg-primary-soft/60 px-3 py-2.5">
                      <p className="text-caption font-semibold text-primary">AI 사전 브리핑</p>
                      <p className="text-caption whitespace-pre-wrap leading-relaxed text-text">
                        {briefing.content}
                      </p>
                    </div>
                  ) : briefing.status === 'failed' ? (
                    <p className="text-caption text-text-secondary">
                      브리핑을 만들지 못했어요 — 상담 진행에는 영향이 없어요
                    </p>
                  ) : briefing.status === 'cancelled' ? null : (
                    <p className="text-caption text-text-secondary">브리핑 생성 중…</p>
                  ))}

                {/* 상태 액션 상시 노출 — 하루 여러 건 처리하는 업무 화면 (05 §5.4) */}
                <div className="flex gap-2">
                  {r.status === 'confirmed' && (
                    <>
                      <Button size="sm" onClick={() => setAction({ id: r.id, status: 'completed' })}>
                        완료 처리
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => setAction({ id: r.id, status: 'no_show' })}
                      >
                        노쇼
                      </Button>
                    </>
                  )}
                  {r.status === 'completed' && (
                    <Button asChild size="sm" variant="secondary">
                      <Link to={`/work/records/${r.id}`}>상담 기록</Link>
                    </Button>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}

      {/* 완료/노쇼는 지표에 바로 반영되는 전이 — 한 번 확인을 거친다 */}
      <Dialog
        open={action !== null}
        onOpenChange={(open) => {
          if (!open) {
            setAction(null)
            transition.reset()
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{action && ACTION_LABEL[action.status]}할까요?</DialogTitle>
            <DialogDescription>
              {target && `${formatTime(target.start_at)} 상담 · ${target.counselor_name}`}
              {action?.status === 'no_show' && (
                <>
                  <br />
                  노쇼 처리하면 고객에게 재예약 안내가 가요.
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          {transition.isError && (
            <p role="alert" className="text-caption text-danger">
              {detailMessage(transition.error, '처리하지 못했어요. 잠시 후 다시 시도해 주세요.')}
            </p>
          )}
          <DialogFooter className="gap-2">
            <Button variant="secondary" onClick={() => setAction(null)}>
              돌아가기
            </Button>
            <Button
              disabled={transition.isPending}
              onClick={() =>
                transition.mutate(
                  { id: action!.id, status: action!.status },
                  { onSuccess: () => setAction(null) },
                )
              }
            >
              {transition.isPending ? '처리 중…' : action && ACTION_LABEL[action.status]}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
