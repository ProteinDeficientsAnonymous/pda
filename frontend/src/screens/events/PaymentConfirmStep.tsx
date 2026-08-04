import { Button } from '@/components/ui/Button';
import type { Event } from '@/models/event';
import { formatPrice } from '@/utils/eventCost';
import { toCashAppUrl, toVenmoUrl } from '@/utils/paymentHandle';

interface Props {
  event: Event;
  busy?: boolean;
  onConfirm: () => void;
  onBack: () => void;
}

export function PaymentConfirmStep({ event, busy = false, onConfirm, onBack }: Props) {
  const links: { label: string; url?: string }[] = [];
  if (event.venmoLink) links.push({ label: 'venmo', url: toVenmoUrl(event.venmoLink) });
  if (event.cashappLink) links.push({ label: 'cashapp', url: toCashAppUrl(event.cashappLink) });
  if (event.zelleInfo) links.push({ label: `zelle: ${event.zelleInfo}` });

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="text-foreground text-sm font-medium">{formatPrice(event.price)}</p>
        <p className="text-foreground-secondary mt-1 text-sm">
          pay the host before you rsvp — then confirm below
        </p>
      </div>

      <ul className="flex flex-col gap-2 text-sm">
        {links.map((link) => (
          <li key={link.label}>
            {link.url ? (
              <a
                href={link.url}
                target="_blank"
                rel="noreferrer"
                className="text-info hover:underline"
              >
                {link.label}
              </a>
            ) : (
              <span className="text-foreground-secondary">{link.label}</span>
            )}
          </li>
        ))}
      </ul>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onBack} disabled={busy}>
          back
        </Button>
        <Button type="button" onClick={onConfirm} disabled={busy}>
          yes, i paid
        </Button>
      </div>
    </div>
  );
}
