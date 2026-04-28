// Static SMS policy page. Linked from the join form's consent checkbox and
// from the URL the org submits to Twilio's toll-free verification form. Stable
// content — don't make this editable, since changing the policy mid-review
// breaks Twilio's verification process.

import { ContentContainer } from './ContentContainer';

export default function SmsPolicyScreen() {
  return (
    <ContentContainer>
      <h1 className="mb-4 text-2xl font-medium tracking-tight">sms policy</h1>

      <p className="text-foreground mb-6 text-sm leading-relaxed">
        when you join pda and provide your phone number, you consent to receive sms messages related
        to community events.
      </p>

      <Section heading="what we send">
        <ul className="text-foreground list-disc pl-5 text-sm leading-relaxed">
          <li>event invitations and confirmations from event hosts</li>
          <li>
            updates about events you've rsvp'd to (e.g. location changes, reminders, cancellations)
          </li>
          <li>
            one-time login links when an admin sends you one (for password resets or initial
            onboarding)
          </li>
        </ul>
      </Section>

      <Section heading="what we don't send">
        <ul className="text-foreground list-disc pl-5 text-sm leading-relaxed">
          <li>marketing or promotional messages</li>
          <li>third-party advertising</li>
          <li>automated marketing sequences</li>
        </ul>
      </Section>

      <Section heading="how we got your consent">
        <p className="text-foreground text-sm leading-relaxed">
          you provided your phone number when you submitted a join request and checked the box
          agreeing to receive sms about events. we record the date of consent on your join request.
        </p>
      </Section>

      <Section heading="how to opt out">
        <ul className="text-foreground list-disc pl-5 text-sm leading-relaxed">
          <li>
            reply <code className="bg-surface-dim rounded px-1">stop</code> to any message to opt
            out of all sms from pda. you'll get one final confirmation, then no further messages.
          </li>
          <li>
            reply <code className="bg-surface-dim rounded px-1">m</code> to mute sms for one
            specific event. you'll stop getting messages about that event but continue to get them
            about others.
          </li>
          <li>contact a community organizer to remove your phone number entirely.</li>
        </ul>
      </Section>

      <Section heading="frequency">
        <p className="text-foreground text-sm leading-relaxed">
          messages are sent only when something happens — an event invite, a host update, etc.
          there's no scheduled or recurring sms. most members get fewer than 10 messages per month.
        </p>
      </Section>

      <Section heading="cost">
        <p className="text-foreground text-sm leading-relaxed">
          standard message and data rates from your carrier may apply. pda does not charge for sms.
        </p>
      </Section>

      <Section heading="contact">
        <p className="text-foreground text-sm leading-relaxed">
          for questions about how we use your phone number, contact a vetting member or admin via
          the community.
        </p>
      </Section>
    </ContentContainer>
  );
}

function Section({ heading, children }: { heading: string; children: React.ReactNode }) {
  return (
    <section className="mb-6">
      <h2 className="text-foreground mb-2 text-sm font-medium tracking-wide">{heading}</h2>
      {children}
    </section>
  );
}
