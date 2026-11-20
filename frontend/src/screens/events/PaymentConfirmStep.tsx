import { Button } from '@/components/ui/Button';
import { buttonClass } from '@/components/ui/buttonClass';
import type { Event } from '@/models/event';
import { cn } from '@/utils/cn';
import { formatPriceWithNote } from '@/utils/eventCost';
import { centsToDollars, formatCents } from '@/utils/orderPrice';
import { toCashAppPayUrl, toVenmoUrl } from '@/utils/paymentHandle';

const PAYMENT_LINK_CLASS = buttonClass('primary', 'w-full');

interface Props {
  event: Event;
  busy?: boolean;
  /** Set for order events: what the guest's picks add up to, used in place of the event price. */
  orderTotalCents?: number | null;
  onConfirm: () => void;
  onBack: () => void;
}

export function PaymentConfirmStep({
  event,
  busy = false,
  orderTotalCents = null,
  onConfirm,
  onBack,
}: Props) {
  const price = orderTotalCents === null ? event.price : centsToDollars(orderTotalCents);
  const links: { label: string; url?: string }[] = [];
  if (event.venmoLink) links.push({ label: 'venmo', url: toVenmoUrl(event.venmoLink) });
  if (event.cashappLink) {
    links.push({
      label: 'cashapp',
      url: toCashAppPayUrl(event.cashappLink, { price }),
    });
  }
  if (event.zelleInfo) links.push({ label: `zelle: ${event.zelleInfo}` });

  return (
    <div className="flex flex-col items-center gap-4 text-center">
      <div>
        <p className="text-foreground text-sm font-medium">
          {orderTotalCents === null
            ? formatPriceWithNote(event)
            : `your total: ${formatCents(orderTotalCents)}`}
        </p>
        <p className="text-foreground-secondary mt-1 text-sm">
          pay the host before you rsvp — then confirm below
        </p>
      </div>

      <div className="flex w-full flex-col gap-2">
        {links.map((link) =>
          link.url ? (
            <a
              key={link.label}
              href={link.url}
              target="_blank"
              rel="noreferrer"
              className={cn(PAYMENT_LINK_CLASS, busy && 'pointer-events-none opacity-50')}
            >
              {link.label}
            </a>
          ) : (
            <p key={link.label} className="text-foreground-secondary text-sm">
              {link.label}
            </p>
          ),
        )}
      </div>

      <Button type="button" variant="secondary" onClick={onConfirm} disabled={busy}>
        yes, i paid
      </Button>
      <button
        type="button"
        onClick={onBack}
        disabled={busy}
        className="text-foreground-tertiary text-xs hover:underline disabled:cursor-not-allowed disabled:opacity-50"
      >
        back
      </button>
    </div>
  );
}
