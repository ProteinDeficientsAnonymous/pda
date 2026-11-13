import { useNavigate } from 'react-router-dom';

import { setStoredRsvpToken } from '@/api/rsvpTokenStorage';
import { type Event, isRsvpDeadlinePassed } from '@/models/event';

import { CostSection } from './EventMemberSection';
import { PublicRsvpForm } from './PublicRsvpForm';
import { RsvpDeadlineNote } from './RsvpDeadline';

interface Props {
  event: Event;
}

export function PublicRsvpSection({ event }: Props) {
  const navigate = useNavigate();

  function unlockWithToken(token: string) {
    // kept out of the url — this page's url is shared, and a token there would leak rsvp identity
    setStoredRsvpToken(token);
    void navigate(0);
  }

  if (isRsvpDeadlinePassed(event)) {
    return (
      <div className="mt-8 flex flex-col gap-6">
        <CostSection event={event} />
        <RsvpDeadlineNote event={event} closed />
      </div>
    );
  }

  return (
    <div className="mt-8 flex flex-col gap-6">
      <CostSection event={event} />
      <PublicRsvpForm
        event={event}
        onSuccess={(result) => {
          unlockWithToken(result.rsvp_token);
        }}
      />
      <RsvpDeadlineNote event={event} closed={false} />
    </div>
  );
}
