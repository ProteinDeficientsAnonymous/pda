import { useMemo, useState } from 'react';

import { TextField } from '@/components/ui/TextField';
import type { Event, RsvpServerStatusValue } from '@/models/event';
import { RsvpServerStatus } from '@/models/event';
import { cn } from '@/utils/cn';

import { GuestChip, InvitedList } from './GuestChip';
import { countWithPlusOnes } from './guestSort';

export type GuestTab = 'going' | 'maybe' | 'cant' | 'waitlist' | 'invited';

const TAB_STATUS: Record<Exclude<GuestTab, 'invited'>, RsvpServerStatusValue> = {
  going: RsvpServerStatus.Attending,
  maybe: RsvpServerStatus.Maybe,
  cant: RsvpServerStatus.CantGo,
  waitlist: RsvpServerStatus.Waitlisted,
};

const TAB_LABELS: Record<GuestTab, string> = {
  going: 'going',
  maybe: 'maybe',
  cant: "can't go",
  waitlist: 'waitlist',
  invited: 'invited',
};

function guestTabs(event: Event, canSeeInvited: boolean): GuestTab[] {
  const tabs: GuestTab[] = ['going', 'maybe'];
  if (!canSeeInvited) return tabs;
  tabs.push('cant');
  if (event.guests.some((g) => g.status === RsvpServerStatus.Waitlisted)) tabs.push('waitlist');
  tabs.push('invited');
  return tabs;
}

interface Props {
  event: Event;
  canSeeInvited: boolean;
  initialTab: GuestTab;
  onClose: () => void;
}

export function GuestListDialog({ event, canSeeInvited, initialTab, onClose }: Props) {
  const tabs = guestTabs(event, canSeeInvited);
  const [active, setActive] = useState<GuestTab>(initialTab);
  const [query, setQuery] = useState('');

  const inTab = useMemo(
    () => (active === 'invited' ? [] : event.guests.filter((g) => g.status === TAB_STATUS[active])),
    [event.guests, active],
  );

  const needle = query.trim().toLowerCase();
  const visible = needle ? inTab.filter((g) => g.name.toLowerCase().includes(needle)) : inTab;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="guest list"
      className="fixed inset-0 z-50 flex items-stretch justify-center sm:items-center sm:p-4"
    >
      <button
        type="button"
        aria-label="close"
        onClick={onClose}
        className="absolute inset-0 cursor-default bg-black/60"
      />
      <div className="bg-surface relative flex h-full w-full flex-col sm:h-auto sm:max-h-[80vh] sm:max-w-md sm:rounded-lg sm:shadow-(--shadow-xl)">
        <div className="flex items-center justify-between gap-2 p-4 pb-2">
          <h2 className="text-base font-medium">guest list</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-foreground-secondary hover:bg-surface-dim rounded-full px-3 py-1 text-sm"
          >
            done
          </button>
        </div>

        <div
          role="tablist"
          aria-label="guest status"
          className="flex gap-1 overflow-x-auto px-4 pb-2"
        >
          {tabs.map((t) => (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={active === t}
              onClick={() => {
                setActive(t);
              }}
              className={cn(
                'shrink-0 rounded-full px-3 py-1.5 text-sm whitespace-nowrap transition-colors',
                active === t
                  ? 'bg-brand-600 text-brand-on'
                  : 'text-foreground-secondary hover:bg-surface-dim',
              )}
            >
              {TAB_LABELS[t]} {tabCount(event, t)}
            </button>
          ))}
        </div>

        {active === 'invited' ? null : (
          <div className="px-4 pb-2">
            <TextField
              label="search guests"
              hideLabel
              type="search"
              placeholder="search guests"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
              }}
            />
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-4 pb-4">
          {active === 'invited' ? (
            <InvitedList event={event} row />
          ) : visible.length === 0 ? (
            <p className="text-muted text-xs">{needle ? 'no one matches' : 'no one yet'}</p>
          ) : (
            <div className="flex flex-col gap-1">
              {visible.map((g) => (
                <GuestChip key={g.userId} guest={g} row />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function tabCount(event: Event, tab: GuestTab): number {
  if (tab === 'invited') return event.invitedCount;
  return countWithPlusOnes(event.guests.filter((g) => g.status === TAB_STATUS[tab]));
}
