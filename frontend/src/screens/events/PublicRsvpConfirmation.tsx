import { Link } from 'react-router-dom';

import type { PublicRsvpOut } from '@/api/publicRsvp';
import type { Event } from '@/models/event';
import { formatEventDateTime } from '@/utils/datetime';
import { ensureHttps } from '@/utils/url';

interface Props {
  event: Event;
  result: PublicRsvpOut;
}

function eventLinks(event: Event): { label: string; url: string }[] {
  const links: { label: string; url: string }[] = [];
  if (event.whatsappLink)
    links.push({ label: 'whatsapp group', url: ensureHttps(event.whatsappLink) });
  if (event.partifulLink) links.push({ label: 'partiful', url: ensureHttps(event.partifulLink) });
  if (event.otherLink) links.push({ label: 'event link', url: ensureHttps(event.otherLink) });
  return links;
}

export function PublicRsvpConfirmation({ event, result }: Props) {
  const attending = result.rsvp.status === 'attending';
  const heading = attending ? "you're in! 🌱" : "you're on the waitlist";
  const links = eventLinks(event);
  return (
    <section
      aria-label="rsvp confirmation"
      className="border-border bg-surface mt-8 rounded-lg border p-6"
    >
      <h2 className="mb-2 text-xl font-medium">{heading}</h2>
      <p className="text-foreground-secondary mb-4 text-sm">
        we just emailed you a link to manage your rsvp — check your inbox
      </p>

      <div className="border-border bg-background mb-4 rounded-md border p-4">
        <p className="text-foreground font-medium">{event.title}</p>
        {event.startDatetime ? (
          <p className="text-foreground-secondary text-sm">
            {formatEventDateTime(event.startDatetime, event.endDatetime, event.datetimeTbd)}
          </p>
        ) : null}
        {event.location ? (
          <p className="text-foreground-secondary text-sm">{event.location}</p>
        ) : null}
        {links.length > 0 ? (
          <ul className="mt-2 flex flex-col gap-1">
            {links.map((l) => (
              <li key={l.url}>
                <a
                  href={l.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-info text-sm hover:underline"
                >
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      <p className="text-foreground-tertiary mb-3 text-sm">want to be part of the community?</p>
      <Link
        to="/join"
        className="border-border-strong text-foreground-secondary hover:bg-background inline-flex h-10 items-center rounded-md border px-4 text-sm font-medium"
      >
        request to join
      </Link>
    </section>
  );
}
