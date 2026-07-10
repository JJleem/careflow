import { cn } from '@/lib/utils'

// CareFlow 자체 심볼 — 바이오컴 민트 톤의 라운드 스퀘어 + 흰 생체신호(pulse) 라인.
// "Flow"(흐름)와 건강 신호를 겹친 시그니처. 브랜드 민트(#22BDB8)는 심볼 배경(그래픽)으로만
// 쓰고, 워드마크 텍스트는 대비를 위해 primary(진민트)를 유지한다 (05 §5.1).
export default function Logo({
  className,
  size = 'md',
  withWordmark = true,
}: {
  className?: string
  size?: 'sm' | 'md'
  withWordmark?: boolean
}) {
  const dim = size === 'sm' ? 20 : 26
  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <svg
        width={dim}
        height={dim}
        viewBox="0 0 24 24"
        role="img"
        aria-label="CareFlow"
        className="shrink-0"
      >
        <rect width="24" height="24" rx="7" fill="var(--cf-color-brand-mint)" />
        <path
          d="M3.5 12.5H8L10 8L13 16L15 11.5H20.5"
          fill="none"
          stroke="#fff"
          strokeWidth="1.9"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {withWordmark && (
        <span
          className={cn(
            'font-extrabold tracking-[-0.02em] text-primary',
            size === 'sm' ? 'text-body' : 'text-title-sm',
          )}
        >
          CareFlow
        </span>
      )}
    </span>
  )
}
