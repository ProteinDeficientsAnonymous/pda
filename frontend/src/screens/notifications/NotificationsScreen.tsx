import { useMarkNotificationRead, useNotificationHistory } from '@/api/notifications';
import { Button } from '@/components/ui/Button';
import { NotificationRow } from '@/layout/NotificationRow';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { reportError } from '@/utils/errorReporter';

const ROUTE = '/notifications';

export default function NotificationsScreen() {
  const { data, isPending, isError, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useNotificationHistory();
  const markRead = useMarkNotificationRead();

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load notifications — try refreshing" />;

  const notifications = data.pages.flat();

  return (
    <ContentContainer>
      <h1 className="mb-6 text-2xl font-medium tracking-tight">notifications</h1>

      {notifications.length === 0 ? (
        <p className="text-muted text-sm">nothing here yet 🌿</p>
      ) : (
        <ul className="border-border divide-y divide-neutral-100 overflow-hidden rounded-lg border">
          {notifications.map((n) => (
            <li key={n.id}>
              <NotificationRow
                n={n}
                onMarkRead={() => {
                  if (!n.isRead) {
                    markRead.mutate(n.id, {
                      onError: (err) => {
                        void reportError(err, ROUTE, {
                          action: 'mark-read',
                          notificationId: n.id,
                        });
                      },
                    });
                  }
                }}
              />
            </li>
          ))}
        </ul>
      )}

      {hasNextPage ? (
        <div className="mt-6 flex justify-center">
          <Button
            variant="secondary"
            disabled={isFetchingNextPage}
            onClick={() => {
              void fetchNextPage();
            }}
          >
            {isFetchingNextPage ? 'loading…' : 'load more'}
          </Button>
        </div>
      ) : null}
    </ContentContainer>
  );
}
