import { Button } from '@/components/ui/Button';
import type { Event } from '@/models/event';
import { cn } from '@/utils/cn';
import { formatPrice } from '@/utils/eventCost';
import { toCashAppPayUrl, toVenmoUrl } from '@/utils/paymentHandle';

const PAYMENT_LINK_CLASS =
  'bg-brand-600 text-brand-on hover:bg-brand-700 inline-flex h-10 w-full items-center justify-center rounded-md px-4 text-sm font-medium transition-colors';

interface Props {
  event: Event;
  busy?: boolean;
  onConfirm: () => void;
  onBack: () => void;
}

export function PaymentConfirmStep({ event, busy = false, onConfirm, onBack }: Props) {
  const links: { label: string; url?: string }[] = [];
  if (event.venmoLink) links.push({ label: 'venmo', url: toVenmoUrl(event.venmoLink) });
  if (event.cashappLink) {
    links.push({
      label: 'cashapp',
      url: toCashAppPayUrl(event.cashappLink, { price: event.price }),
    });
  }
  if (event.zelleInfo) links.push({ label: `zelle: ${event.zelleInfo}` });

  return (
    <div className="flex flex-col items-center gap-4 text-center">
      <div>
        <p className="text-foreground text-sm font-medium">{formatPrice(event.price)}</p>
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
