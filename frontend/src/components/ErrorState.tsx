import { Button } from '@/components/ui/button'

// 에러 상태 의무 구현 (05 §5.5-4) — 무엇이 잘못됐는지 + 다시 시도 경로
export default function ErrorState({
  message = '정보를 불러오지 못했어요.',
  onRetry,
}: {
  message?: string
  onRetry?: () => void
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-card bg-card px-6 py-14 text-center shadow-card">
      <p className="font-semibold">{message}</p>
      <p className="text-caption text-text-secondary">네트워크 상태를 확인하고 다시 시도해 주세요</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          다시 시도
        </Button>
      )}
    </div>
  )
}
