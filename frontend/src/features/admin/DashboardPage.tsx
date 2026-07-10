import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMetrics } from '../../api/queries/admin'
import { useAuthStore } from '../../auth/store'
import { toDateParam } from '../../lib/datetime'
import ErrorState from '../../components/ErrorState'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

const RANGES = [
  { label: '최근 7일', days: 7 },
  { label: '최근 30일', days: 30 },
  { label: '최근 90일', days: 90 },
] as const

/** 비율(0~1) → "62.5%". null(해당 기간 0건)은 "—" — 0%와 구분 (docs/06 §6.7) */
function pct(v: number | null | undefined) {
  return v == null ? '—' : `${(v * 100).toFixed(1)}%`
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const logout = useAuthStore((s) => s.logout)
  const [rangeDays, setRangeDays] = useState<number>(30)

  const { from, to } = useMemo(() => {
    const now = new Date()
    return {
      from: toDateParam(new Date(now.getTime() - (rangeDays - 1) * 86_400_000)),
      to: toDateParam(now),
    }
  }, [rangeDays])

  const metrics = useMetrics(from, to)

  return (
    <div className="min-h-screen bg-surface">
      <header className="sticky top-0 z-10 bg-bg/90 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-4xl items-center gap-3 px-4">
          <span className="text-title-sm font-extrabold tracking-[-0.02em] text-primary">
            CareFlow
          </span>
          <span className="rounded-pill bg-surface px-2 py-0.5 text-caption font-semibold text-text-secondary">
            관리자
          </span>
          <button
            type="button"
            onClick={() => {
              logout()
              navigate('/login')
            }}
            className="ml-auto text-caption text-text-secondary transition-colors hover:text-text"
          >
            로그아웃
          </button>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-4xl flex-col gap-5 px-4 py-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-title-md">운영 지표</h1>
          <div className="flex gap-1 rounded-pill bg-card p-1 shadow-card">
            {RANGES.map((r) => (
              <button
                key={r.days}
                type="button"
                onClick={() => setRangeDays(r.days)}
                className={cn(
                  'rounded-pill px-3 py-1.5 text-caption font-semibold transition-colors',
                  rangeDays === r.days ? 'bg-primary text-primary-foreground' : 'text-text-secondary',
                )}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        {metrics.isPending ? (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-28 rounded-card" />
            ))}
          </div>
        ) : metrics.isError ? (
          <ErrorState onRetry={() => metrics.refetch()} />
        ) : (
          <>
            {/* 지표 카드 4종 — 숫자가 주인공, 색은 primary·neutral·warning으로 제한 (05 §5.4) */}
            <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <MetricCard label="총 예약" value={`${metrics.data.total_reservations}건`} />
              <MetricCard label="완료율" value={pct(metrics.data.completion_rate)} accent="primary" />
              <MetricCard
                label="노쇼율"
                value={pct(metrics.data.no_show_rate)}
                accent={metrics.data.no_show_rate ? 'warning' : undefined}
              />
              <MetricCard label="구매 전환율" value={pct(metrics.data.conversion_rate)} accent="primary" />
            </section>

            {/* 예약 상태 분해 — 위 완료율/노쇼율의 분자·분모를 눈으로 확인 */}
            <section className="grid grid-cols-2 gap-3 rounded-card bg-card p-5 shadow-card sm:grid-cols-4">
              <Stat label="완료" value={metrics.data.completed} />
              <Stat label="노쇼" value={metrics.data.no_show} />
              <Stat label="취소" value={metrics.data.cancelled} />
              <Stat label="예정" value={metrics.data.confirmed_upcoming} />
            </section>

            <section className="flex flex-col gap-3 rounded-card bg-card p-5 shadow-card">
              <h2 className="font-bold">관심 제품 순위</h2>
              {metrics.data.top_interested_products.length === 0 ? (
                <p className="py-6 text-center text-caption text-text-secondary">
                  이 기간에 기록된 관심 제품이 없어요
                </p>
              ) : (
                <ProductRanking items={metrics.data.top_interested_products} />
              )}
            </section>

            <p className="text-caption text-text-secondary">
              {from} ~ {to} · Asia/Seoul 기준
            </p>
          </>
        )}
      </main>
    </div>
  )
}

function MetricCard({
  label,
  value,
  accent,
}: {
  label: string
  value: string
  accent?: 'primary' | 'warning'
}) {
  return (
    <div className="flex flex-col gap-1.5 rounded-card bg-card p-5 shadow-card">
      <span className="text-caption text-text-secondary">{label}</span>
      <span
        className={cn(
          'text-metric font-bold tabular-nums tracking-[-0.02em]',
          accent === 'primary' && 'text-primary',
          accent === 'warning' && 'text-warning',
        )}
      >
        {value}
      </span>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span className="text-title-sm font-bold tabular-nums">{value}</span>
      <span className="text-caption text-text-secondary">{label}</span>
    </div>
  )
}

function ProductRanking({ items }: { items: { product: string; count: number }[] }) {
  const max = Math.max(...items.map((i) => i.count))
  return (
    <ol className="flex flex-col gap-2.5">
      {items.map((item, i) => (
        <li key={item.product} className="flex items-center gap-3">
          <span className="w-4 text-caption font-bold tabular-nums text-text-secondary">{i + 1}</span>
          <span className="w-28 shrink-0 truncate font-semibold">{item.product}</span>
          <div className="h-2 flex-1 overflow-hidden rounded-pill bg-surface">
            <div
              className="h-full rounded-pill bg-primary"
              style={{ width: `${(item.count / max) * 100}%` }}
            />
          </div>
          <span className="w-8 text-right text-caption tabular-nums text-text-secondary">
            {item.count}
          </span>
        </li>
      ))}
    </ol>
  )
}
