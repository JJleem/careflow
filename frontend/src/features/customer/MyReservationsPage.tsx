import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMyReservations, useTransitionReservation } from '../../api/queries/reservations'
import { detailMessage } from '../../api/error'
import { formatDate, formatTime } from '../../lib/datetime'
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

export default function MyReservationsPage() {
  const reservations = useMyReservations()
  const transition = useTransitionReservation()
  const [cancelTarget, setCancelTarget] = useState<number | null>(null)

  if (reservations.isPending) {
    return (
      <div className="flex flex-col gap-3">
        <h1 className="text-title-md">내 예약</h1>
        {[0, 1].map((i) => (
          <Skeleton key={i} className="h-28 rounded-card" />
        ))}
      </div>
    )
  }
  if (reservations.isError) return <ErrorState onRetry={() => reservations.refetch()} />

  const now = Date.now()
  const upcoming = reservations.data
    .filter((r) => r.status === 'confirmed' && new Date(r.start_at).getTime() > now)
    .sort((a, b) => a.start_at.localeCompare(b.start_at))
  const past = reservations.data
    .filter((r) => !upcoming.includes(r))
    .sort((a, b) => b.start_at.localeCompare(a.start_at))

  const target = reservations.data.find((r) => r.id === cancelTarget)

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-title-md">내 예약</h1>

      {reservations.data.length === 0 && (
        <EmptyState
          title="예약한 상담이 없어요"
          description="결과지에서 전화 상담을 예약할 수 있어요"
          action={
            <Button asChild variant="secondary" size="sm">
              <Link to="/results">결과지 보러 가기</Link>
            </Button>
          }
        />
      )}

      {upcoming.length > 0 && (
        <section className="flex flex-col gap-3" aria-label="다가오는 상담">
          <h2 className="text-caption font-semibold text-text-secondary">다가오는 상담</h2>
          {upcoming.map((r) => (
            <article key={r.id} className="flex flex-col gap-3 rounded-card bg-card p-5 shadow-card">
              <div className="flex items-center justify-between">
                <StatusBadge status={r.status} audience="customer" />
                <button
                  type="button"
                  onClick={() => {
                    transition.reset()
                    setCancelTarget(r.id)
                  }}
                  className="text-caption text-text-secondary transition-colors hover:text-danger"
                >
                  취소
                </button>
              </div>
              <div className="flex flex-col gap-0.5">
                <p className="text-title-sm font-bold tabular-nums">
                  {formatDate(r.start_at)} {formatTime(r.start_at)}
                </p>
                <p className="text-caption text-text-secondary">{r.counselor_name} 상담사 · 전화 상담</p>
              </div>
              {r.pre_question && (
                <p className="rounded-chip bg-surface px-3 py-2 text-caption text-text-secondary">
                  사전 문의 — {r.pre_question}
                </p>
              )}
            </article>
          ))}
        </section>
      )}

      {past.length > 0 && (
        <section className="flex flex-col gap-3" aria-label="지난 내역">
          <h2 className="text-caption font-semibold text-text-secondary">지난 내역</h2>
          {past.map((r) => (
            <article key={r.id} className="flex flex-col gap-3 rounded-card bg-card p-5 shadow-card">
              <div className="flex items-center gap-3">
                <div className="flex flex-1 flex-col gap-0.5">
                  <p className="font-semibold tabular-nums">
                    {formatDate(r.start_at)} {formatTime(r.start_at)}
                  </p>
                  <p className="text-caption text-text-secondary">{r.counselor_name} 상담사</p>
                </div>
                <StatusBadge status={r.status} audience="customer" />
              </div>
              {/* 미진행(노쇼) 상담은 재예약으로 유도 — 이탈 방지(P3) 접점 */}
              {r.status === 'no_show' && (
                <div className="flex items-center justify-between gap-3 rounded-chip bg-surface px-3 py-2.5">
                  <span className="text-caption text-text-secondary">상담이 진행되지 못했어요</span>
                  <Button asChild size="sm">
                    <Link to={`/reserve?result=${r.test_result_id}&subject=${r.subject_id}`}>
                      다시 예약하기
                    </Link>
                  </Button>
                </div>
              )}
            </article>
          ))}
        </section>
      )}

      {/* 취소는 복구할 수 없는 상태 전이 — 확인을 거친다 */}
      <Dialog open={cancelTarget !== null} onOpenChange={(open) => !open && setCancelTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>예약을 취소할까요?</DialogTitle>
            <DialogDescription>
              {target && `${formatDate(target.start_at)} ${formatTime(target.start_at)} · ${target.counselor_name} 상담사`}
              <br />
              취소한 자리는 다른 분에게 열려요.
            </DialogDescription>
          </DialogHeader>
          {transition.isError && (
            <p role="alert" className="text-caption text-danger">
              {detailMessage(transition.error, '취소하지 못했어요. 잠시 후 다시 시도해 주세요.')}
            </p>
          )}
          <DialogFooter className="gap-2">
            <Button variant="secondary" onClick={() => setCancelTarget(null)}>
              돌아가기
            </Button>
            <Button
              variant="destructive"
              disabled={transition.isPending}
              onClick={() =>
                transition.mutate(
                  { id: cancelTarget!, status: 'cancelled' },
                  { onSuccess: () => setCancelTarget(null) },
                )
              }
            >
              {transition.isPending ? '취소 중…' : '예약 취소'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
