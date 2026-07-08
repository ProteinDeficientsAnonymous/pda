import { toast } from 'sonner';

import { useCalendarToken, useRegenerateCalendarToken } from '@/api/calendar';
import { Button } from '@/components/ui/Button';
import { useConfirm } from '@/components/ui/useConfirm';

export function CalendarFeedSubscription() {
  const tokenQ = useCalendarToken();
  const regenerate = useRegenerateCalendarToken();
  const { confirm, element: confirmElement } = useConfirm();

  if (tokenQ.isPending) {
    return <p className="text-muted text-sm">loading feed link…</p>;
  }
  if (tokenQ.isError) {
    return <p className="text-muted text-sm">couldn't load calendar feed — try again later</p>;
  }

  const feedUrl = tokenQ.data.feedUrl;

  async function copyFeedUrl() {
    try {
      await navigator.clipboard.writeText(feedUrl);
      toast.success('feed link copied 🌱');
    } catch {
      toast.error("couldn't copy — try selecting the text");
    }
  }

  async function handleRegenerate() {
    const ok = await confirm({
      title: 'revoke and create new link?',
      message:
        "this will break any calendar already subscribed to your old link — you'll need to resubscribe everywhere. only do this if your link leaked or you want to revoke shared access.",
      confirmLabel: 'revoke and create new',
      cancelLabel: 'cancel',
      destructive: true,
    });
    if (!ok) return;
    try {
      await regenerate.mutateAsync();
      toast.success('new feed link generated 🌱');
    } catch {
      toast.error("couldn't regenerate feed link");
    }
  }

  return (
    <div className="border-border flex flex-col gap-2 border-t pt-4">
      <p className="text-muted text-xs">
        subscribe to the community calendar in apple calendar, google calendar, etc — paste the
        private url once and it'll stay in sync. step-by-step instructions below.
      </p>
      <label className="text-muted text-xs" htmlFor="cal-feed-url">
        feed url
      </label>
      <input
        id="cal-feed-url"
        readOnly
        className="border-border bg-background text-foreground w-full rounded-md border px-3 py-2 font-mono text-xs"
        value={feedUrl}
      />
      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="primary" onClick={() => void copyFeedUrl()}>
          copy link
        </Button>
        <Button
          type="button"
          variant="secondary"
          disabled={regenerate.isPending}
          onClick={() => void handleRegenerate()}
        >
          {regenerate.isPending ? 'generating…' : 'revoke and create new link'}
        </Button>
      </div>
      <CalendarFeedHowTo />
      {confirmElement}
    </div>
  );
}

function CalendarFeedHowTo() {
  return (
    <details className="border-border mt-1 rounded-md border px-3 py-2 text-sm">
      <summary className="text-foreground cursor-pointer font-medium">
        how to add this to your calendar
      </summary>
      <div className="text-muted mt-3 flex flex-col gap-4">
        <div>
          <p className="text-foreground font-medium">apple calendar (iphone / ipad)</p>
          <ol className="mt-1 ml-4 list-decimal space-y-0.5 text-xs">
            <li>copy the feed url above</li>
            <li>open the settings app, tap apps → calendar → calendar accounts</li>
            <li>tap add account → other → add subscribed calendar, paste the url, then save</li>
          </ol>
          <a
            className="text-brand-700 mt-1 inline-block text-xs underline"
            href="https://support.apple.com/en-us/102301"
            target="_blank"
            rel="noopener noreferrer"
          >
            apple's full instructions ↗
          </a>
        </div>

        <div>
          <p className="text-foreground font-medium">apple calendar (mac)</p>
          <p className="mt-1 text-xs">
            in the calendar app: file → new calendar subscription, paste the url, choose your
            account, click subscribe.
          </p>
        </div>

        <div>
          <p className="text-foreground font-medium">google calendar (desktop only)</p>
          <p className="mt-1 text-xs">
            this can't be done from the google calendar phone app — use a computer. on
            calendar.google.com, click the + next to "other calendars" → from url, paste the feed
            url, then add calendar. it'll show up on your phone once it syncs.
          </p>
          <a
            className="text-brand-700 mt-1 inline-block text-xs underline"
            href="https://support.google.com/calendar/answer/37100"
            target="_blank"
            rel="noopener noreferrer"
          >
            google's full instructions ↗
          </a>
        </div>

        <div>
          <p className="text-foreground font-medium">outlook</p>
          <a
            className="text-brand-700 mt-1 inline-block text-xs underline"
            href="https://support.microsoft.com/en-us/office/import-or-subscribe-to-a-calendar-in-outlook-com-or-outlook-on-the-web-cff1429c-5af6-41ec-a5b4-74f2c278e98c"
            target="_blank"
            rel="noopener noreferrer"
          >
            microsoft's instructions ↗
          </a>
        </div>
      </div>
    </details>
  );
}
