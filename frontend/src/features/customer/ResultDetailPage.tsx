import { Link, useNavigate, useParams } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import { useConsultToken, useSubjects, useTestResult } from '../../api/queries/results'
import { SERVICE_TYPE_LABEL, isOutOfRange } from '../../lib/labels'
import { formatDateOnly } from '../../lib/datetime'
import ErrorState from '../../components/ErrorState'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface Indicator {
  name?: string
  value?: number
  unit?: string
  range?: string
  comment?: string
}

export default function ResultDetailPage() {
  const { id } = useParams()
  const testResultId = Number(id)
  const navigate = useNavigate()
  const result = useTestResult(testResultId)
  const subjects = useSubjects()
  const qr = useConsultToken(testResultId)

  if (result.isPending) {
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-36 rounded-card" />
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-28 rounded-card" />
        ))}
      </div>
    )
  }
  if (result.isError) return <ErrorState onRetry={() => result.refetch()} />

  const data = result.data
  const subject = subjects.data?.find((s) => s.id === data.subject_id)
  const indicators = data.indicators as Indicator[]

  return (
    <div className="flex flex-col gap-4">
      <Link to="/results" className="text-caption text-text-secondary hover:text-text">
        ‹ 결과지 목록
      </Link>

      {/* 결과 요약 히어로 — 딥 틸은 이 강조 배경에만 사용 (05 §5.4) */}
      <section className="flex flex-col gap-1.5 rounded-card bg-deep p-6 text-white shadow-card">
        <p className="text-caption font-semibold text-brand-mint">
          {SERVICE_TYPE_LABEL[data.service_type]}
        </p>
        <h1 className="text-title-md text-white">
          {subject ? `${subject.name}님의 검사 결과` : '검사 결과'}
        </h1>
        <p className="text-caption text-white/60">{formatDateOnly(data.reported_at)} 발행</p>
      </section>

      <section className="flex flex-col gap-3" aria-label="검사 지표">
        {indicators.map((ind, i) => {
          const out =
            typeof ind.value === 'number' && ind.range ? isOutOfRange(ind.value, ind.range) : null
          return (
            <article key={i} className="flex flex-col gap-2 rounded-card bg-card p-5 shadow-card">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-body font-bold">{ind.name}</h2>
                {out !== null && (
                  <span
                    className={cn(
                      'rounded-pill px-2.5 py-0.5 text-caption font-semibold',
                      out ? 'bg-warning/10 text-warning' : 'bg-primary-soft text-primary',
                    )}
                  >
                    {out ? '주의' : '정상'}
                  </span>
                )}
              </div>
              <p className="flex items-baseline gap-1.5">
                <span className="text-metric font-bold tabular-nums tracking-[-0.02em]">
                  {ind.value}
                </span>
                <span className="text-caption text-text-secondary">{ind.unit}</span>
                {ind.range && (
                  <span className="ml-auto text-caption text-text-secondary">
                    참고 범위 {ind.range}
                  </span>
                )}
              </p>
              {ind.comment && <p className="text-caption leading-relaxed text-text-secondary">{ind.comment}</p>}
            </article>
          )
        })}
      </section>

      <Button
        className="w-full"
        onClick={() => navigate(`/reserve?result=${data.id}&subject=${data.subject_id}`)}
      >
        이 결과로 상담 예약하기
      </Button>

      {/* 실물 결과지의 QR과 동일한 서명 토큰 — 가족 등 결과지를 받은 사람이 스캔해 바로 예약 (docs/04 §4.7) */}
      {qr.data && (
        <section className="flex items-center gap-5 rounded-card bg-card p-5 shadow-card">
          <div className="shrink-0 rounded-chip bg-white p-2">
            <QRCodeSVG value={`${window.location.origin}${qr.data.url}`} size={96} />
          </div>
          <div className="flex flex-col gap-1">
            <h2 className="text-body font-bold">전화 상담 예약 QR</h2>
            <p className="text-caption leading-relaxed text-text-secondary">
              결과지를 받은 분이 스캔하면 로그인 없이 본인확인만으로 예약할 수 있어요. 열린 화면은
              30분 동안 유효해요.
            </p>
          </div>
        </section>
      )}
    </div>
  )
}
