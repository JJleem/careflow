import type { ReactNode } from 'react'

// 모든 목록 화면의 빈 상태 의무 구현 (05 §5.5-4) — 빈 화면은 행동 안내로 대체
export default function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-card bg-card px-6 py-14 text-center shadow-card">
      <p className="font-semibold">{title}</p>
      {description && <p className="text-caption text-text-secondary">{description}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  )
}
