import { Link } from 'react-router-dom'
import { useSubjects, useSubjectResults } from '../../api/queries/results'
import { SERVICE_TYPE_LABEL, SERVICE_METHOD, RELATION_LABEL } from '../../lib/labels'
import { formatDateOnly } from '../../lib/datetime'
import EmptyState from '../../components/EmptyState'
import ErrorState from '../../components/ErrorState'
import { Skeleton } from '@/components/ui/skeleton'

export default function ResultsListPage() {
  const subjects = useSubjects()
  const resultQueries = useSubjectResults(subjects.data?.map((s) => s.id) ?? [])

  if (subjects.isPending || resultQueries.some((q) => q.isPending)) {
    return (
      <div className="flex flex-col gap-3">
        <h1 className="text-title-md">내 검사 결과</h1>
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-24 rounded-card" />
        ))}
      </div>
    )
  }
  if (subjects.isError) return <ErrorState onRetry={() => subjects.refetch()} />

  const rows = (subjects.data ?? []).flatMap((subject, i) =>
    (resultQueries[i]?.data ?? []).map((result) => ({ subject, result })),
  )

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-title-md">내 검사 결과</h1>
      {rows.length === 0 ? (
        <EmptyState
          title="아직 도착한 결과지가 없어요"
          description="분석이 완료되면 여기에서 확인할 수 있어요"
        />
      ) : (
        <ul className="flex flex-col gap-3">
          {rows.map(({ subject, result }) => (
            <li key={result.id}>
              <Link
                to={`/results/${result.id}`}
                className="flex items-center gap-4 rounded-card bg-card p-5 shadow-card transition-transform active:scale-[0.99]"
              >
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                  <span className="flex items-center gap-2">
                    <span className="font-bold">{SERVICE_TYPE_LABEL[result.service_type]}</span>
                    <span className="rounded-pill bg-surface px-2 py-0.5 text-caption text-text-secondary">
                      {SERVICE_METHOD[result.service_type]}
                    </span>
                  </span>
                  <span className="text-caption text-text-secondary">
                    {subject.name} ({RELATION_LABEL[subject.relation]}) ·{' '}
                    {formatDateOnly(result.reported_at)} 발행
                  </span>
                </div>
                <span aria-hidden className="text-text-secondary">
                  ›
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
