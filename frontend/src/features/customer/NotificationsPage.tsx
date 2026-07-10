import { useMarkRead, useNotifications } from '../../api/queries/notifications'
import { NOTIFICATION_LABEL } from '../../lib/labels'
import { formatDateTime } from '../../lib/datetime'
import EmptyState from '../../components/EmptyState'
import ErrorState from '../../components/ErrorState'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

export default function NotificationsPage() {
  const notifications = useNotifications()
  const markRead = useMarkRead()

  if (notifications.isPending) {
    return (
      <div className="flex flex-col gap-3">
        <h1 className="text-title-md">알림</h1>
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-20 rounded-card" />
        ))}
      </div>
    )
  }
  if (notifications.isError) return <ErrorState onRetry={() => notifications.refetch()} />

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-title-md">알림</h1>
      {notifications.data.length === 0 ? (
        <EmptyState
          title="아직 알림이 없어요"
          description="예약 확정, 상담 전 리마인드를 여기로 보내드려요"
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {notifications.data.map((n) => (
            <li key={n.id}>
              <button
                type="button"
                onClick={() => !n.read && markRead.mutate(n.id)}
                className={cn(
                  'flex w-full flex-col gap-1 rounded-card p-4 text-left transition-colors',
                  n.read ? 'bg-card/60 text-text-secondary' : 'bg-card shadow-card',
                )}
              >
                <span className="flex items-center gap-2">
                  {!n.read && <span aria-label="읽지 않음" className="size-1.5 rounded-pill bg-primary" />}
                  <span className={cn('text-caption font-semibold', n.read ? '' : 'text-primary')}>
                    {NOTIFICATION_LABEL[n.type]}
                  </span>
                  <span className="ml-auto text-caption text-text-secondary tabular-nums">
                    {formatDateTime(n.scheduled_at)}
                  </span>
                </span>
                <span className={cn('text-body', n.read && 'text-text-secondary')}>{n.message}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
