import { Link } from 'react-router-dom';

import type { PublicRsvpOut } from '@/api/publicRsvp';
import type { Event } from '@/models/event';
import { RsvpServerStatus } from '@/models/event';
import { buildEventLinks } from '@/utils/eventLinks';

interface Props {
  event: Event;
  result: PublicRsvpOut;
}

const STATUS_HEADINGS: Record<string, string> = {
  [RsvpServerStatus.Attending]: "you're in! 🌱",
  [RsvpServerStatus.Waitlisted]: "you're on the waitlist",
  [RsvpServerStatus.Maybe]: "you're down as a maybe",
  [RsvpServerStatus.CantGo]: 'thanks for letting us know',
};

export function PublicRsvpConfirmation({ event, result }: Props) {
  const heading = STATUS_HEADINGS[result.rsvp.status] ?? 'thanks for your rsvp';
  const links = buildEventLinks(event);
  const hasExtraInfo = Boolean(event.location) || links.length > 0;
  return (
    <section
      aria-label="rsvp confirmation"
      className="border-border bg-surface mt-8 rounded-lg border p-6"
    >
      <h2 className="mb-2 text-xl font-medium">{heading}</h2>
      <p className="text-foreground-secondary mb-4 text-sm">
        we just emailed you a link to manage your rsvp — check your inbox
      </p>

      {hasExtraInfo ? (
        <div className="border-border bg-background mb-4 rounded-md border p-4">
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
      ) : null}

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
