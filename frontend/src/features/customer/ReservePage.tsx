import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAvailableTimes, useCreateReservation } from '../../api/queries/reservations'
import { getScopedSession } from '../../auth/scopedSession'
import { useAuthStore } from '../../auth/store'
import { ApiError } from '../../api/error'
import { formatDate, formatDateOnly, formatTime, toDateParam, upcomingDays } from '../../lib/datetime'
import ErrorState from '../../components/ErrorState'
import EmptyState from '../../components/EmptyState'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

interface FullConflict {
  message?: string
  alternative_times?: { start_at: string; available_count: number }[]
  alternative_dates?: { date: string; available_count: number }[]
}

export default function ReservePage() {
  const [params] = useSearchParams()
  const user = useAuthStore((s) => s.user)
  const scoped = getScopedSession()

  // 예약 컨텍스트: 결과지 상세 CTA(쿼리 파라미터) 또는 QR 스코프 세션.
  // 예약은 항상 특정 결과지에 대한 상담이므로 컨텍스트 없이는 시작할 수 없다.
  const testResultId = Number(params.get('result')) || scoped?.testResultId
  const subjectId = Number(params.get('subject')) || scoped?.subjectId

  const days = useMemo(() => upcomingDays(14), [])
  const [date, setDate] = useState(() => toDateParam(new Date()))
  const [selectedTime, setSelectedTime] = useState<string | null>(null)
  const [preQuestion, setPreQuestion] = useState('')

  const slots = useAvailableTimes(date)
  const create = useCreateReservation()

  if (!testResultId || !subjectId) {
    return (
      <EmptyState
        title="어떤 검사에 대한 상담인지 알려주세요"
        description="결과지에서 상담 예약을 시작할 수 있어요"
        action={
          user ? (
            <Button asChild variant="secondary" size="sm">
              <Link to="/results">결과지 보러 가기</Link>
            </Button>
          ) : (
            <Button asChild variant="secondary" size="sm">
              <Link to="/login">로그인</Link>
            </Button>
          )
        }
      />
    )
  }

  // 예약 확정 — 폼 대신 확인 화면으로 전환
  if (create.isSuccess) {
    const r = create.data
    return (
      <div className="flex flex-col gap-4">
        <section className="flex flex-col items-center gap-2 rounded-card bg-card px-6 py-12 text-center shadow-card">
          <span className="flex size-12 items-center justify-center rounded-pill bg-primary-soft text-title-md text-primary">
            ✓
          </span>
          <h1 className="text-title-md">예약이 확정됐어요</h1>
          <p className="text-body text-text-secondary">
            {formatDate(r.start_at)} {formatTime(r.start_at)} · {r.counselor_name} 상담사
          </p>
          <p className="text-caption text-text-secondary">
            예약한 번호로 상담 전화를 드려요. 하루 전과 1시간 전에 알림으로 알려드릴게요.
          </p>
        </section>
        {user ? (
          <Button asChild className="w-full">
            <Link to="/my/reservations">내 예약 보기</Link>
          </Button>
        ) : (
          <p className="text-center text-caption text-text-secondary">
            이 창은 닫아도 돼요. 예약 관리는 가입 계정에서 할 수 있어요.
          </p>
        )}
      </div>
    )
  }

  const conflict =
    create.error instanceof ApiError && typeof create.error.detail === 'object'
      ? (create.error.detail as FullConflict)
      : null
  const conflictMessage =
    create.error instanceof ApiError && typeof create.error.detail === 'string'
      ? create.error.detail
      : null

  function submit() {
    if (!selectedTime) return
    create.mutate({
      start_at: selectedTime,
      subject_id: subjectId!,
      test_result_id: testResultId!,
      pre_question: preQuestion.trim() || null,
    })
  }

  function pickTime(startAt: string) {
    setSelectedTime(startAt)
    create.reset() // 이전 409 안내 제거
  }

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-title-md">전화 상담 예약</h1>

      <section className="flex flex-col gap-2">
        <Label>날짜</Label>
        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
          {days.map((d) => (
            <button
              key={d.value}
              type="button"
              onClick={() => {
                setDate(d.value)
                setSelectedTime(null)
                create.reset()
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
            </button>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-2">
        <Label>시간</Label>
        {slots.isPending ? (
          <Skeleton className="h-28 rounded-card" />
        ) : slots.isError ? (
          <ErrorState onRetry={() => slots.refetch()} />
        ) : slots.data.times.length === 0 ? (
          // 만석 시 대안 안내가 빈 화면을 대체한다 (05 §5.5-4)
          <div className="flex flex-col gap-3 rounded-card bg-card p-5 shadow-card">
            <p className="font-semibold">이 날짜는 모두 마감됐어요</p>
            {slots.data.alternatives.length > 0 ? (
              <>
                <p className="text-caption text-text-secondary">가장 가까운 예약 가능일이에요</p>
                <div className="flex flex-wrap gap-2">
                  {slots.data.alternatives.map((alt) => (
                    <button
                      key={alt.date}
                      type="button"
                      onClick={() => {
                        setDate(alt.date)
                        setSelectedTime(null)
                      }}
                      className="rounded-pill bg-primary-soft px-3.5 py-1.5 text-caption font-semibold text-primary transition-transform active:scale-[0.97]"
                    >
                      {formatDateOnly(alt.date)} · {alt.available_count}자리
                    </button>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-caption text-text-secondary">다른 날짜를 선택해 주세요</p>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-2">
            {slots.data.times.map((t) => (
              <button
                key={t.start_at}
                type="button"
                onClick={() => pickTime(t.start_at)}
                className={cn(
                  'flex flex-col items-center rounded-control py-2.5 transition-colors',
                  selectedTime === t.start_at
                    ? 'bg-primary font-semibold text-primary-foreground'
                    : 'bg-card shadow-card',
                )}
              >
                <span className="text-body font-semibold tabular-nums">{formatTime(t.start_at)}</span>
                <span
                  className={cn(
                    'text-caption',
                    selectedTime === t.start_at ? 'text-white/70' : 'text-text-secondary',
                  )}
                >
                  {t.available_count}자리
                </span>
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="flex flex-col gap-2">
        <Label htmlFor="pre-question">미리 물어보고 싶은 것 (선택)</Label>
        <Textarea
          id="pre-question"
          placeholder="상담에서 꼭 다루고 싶은 내용을 적어주시면 상담사가 미리 준비해요"
          maxLength={2000}
          value={preQuestion}
          onChange={(e) => setPreQuestion(e.target.value)}
        />
      </section>

      {/* 방금 마감된 경우(409) — 서버가 준 대안을 그대로 제시 (docs/06 §6.5) */}
      {conflict && (
        <div className="flex flex-col gap-3 rounded-card bg-warning/10 p-5">
          <p className="font-semibold text-warning">선택한 시간이 방금 마감됐어요</p>
          {(conflict.alternative_times?.length ?? 0) > 0 && (
            <>
              <p className="text-caption text-text-secondary">같은 날 이 시간은 가능해요</p>
              <div className="flex flex-wrap gap-2">
                {conflict.alternative_times!.map((t) => (
                  <button
                    key={t.start_at}
                    type="button"
                    onClick={() => pickTime(t.start_at)}
                    className="rounded-pill bg-card px-3.5 py-1.5 text-caption font-semibold text-primary shadow-card transition-transform active:scale-[0.97]"
                  >
                    {formatTime(t.start_at)} · {t.available_count}자리
                  </button>
                ))}
              </div>
            </>
          )}
          {(conflict.alternative_dates?.length ?? 0) > 0 && (
            <>
              <p className="text-caption text-text-secondary">이 날짜로 옮길 수도 있어요</p>
              <div className="flex flex-wrap gap-2">
                {conflict.alternative_dates!.map((d) => (
                  <button
                    key={d.date}
                    type="button"
                    onClick={() => {
                      setDate(d.date)
                      setSelectedTime(null)
                      create.reset()
                    }}
                    className="rounded-pill bg-card px-3.5 py-1.5 text-caption font-semibold text-primary shadow-card transition-transform active:scale-[0.97]"
                  >
                    {formatDateOnly(d.date)} · {d.available_count}자리
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      )}
      {conflictMessage && (
        <p role="alert" className="text-caption text-danger">
          {conflictMessage}
        </p>
      )}

      <Button className="w-full" disabled={!selectedTime || create.isPending} onClick={submit}>
        {create.isPending
          ? '예약 중…'
          : selectedTime
            ? `${formatTime(selectedTime)} 예약하기`
            : '시간을 선택해 주세요'}
      </Button>
    </div>
  )
}
