import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

vi.mock('@/api/featureFlags', () => ({
  useFlag: vi.fn(),
}));
vi.mock('./EmailBlastDialog', () => ({
  EmailBlastDialog: ({ open }: { open: boolean }) =>
    open ? <div data-testid="email-blast-dialog" /> : null,
}));
vi.mock('./GroupTextDialog', () => ({
  GroupTextDialog: ({ open }: { open: boolean }) =>
    open ? <div data-testid="group-text-dialog" /> : null,
}));

import { useFlag } from '@/api/featureFlags';
import type { Event } from '@/models/event';
import { EventStatus } from '@/models/event';
import { makeEvent } from '@/test/fixtures';

import { EventDetailKebabMenu } from './EventDetailKebabMenu';

function renderMenu(
  overrides: {
    eventHasEnded?: boolean;
    canManageRsvps?: boolean;
    event?: Partial<Event>;
  } = {},
) {
  return render(
    <MemoryRouter>
      <EventDetailKebabMenu
        event={makeEvent(overrides.event)}
        eventHasEnded={overrides.eventHasEnded ?? false}
        canManageRsvps={overrides.canManageRsvps ?? false}
      />
    </MemoryRouter>,
  );
}

async function openMenu() {
  await userEvent.click(screen.getByRole('button', { name: /event settings/i }));
}

describe('EventDetailKebabMenu', () => {
  it('shows a check-in item linking to the attendance route', async () => {
    vi.mocked(useFlag).mockReturnValue(false);
    renderMenu();
    await openMenu();

    const checkIn = screen.getByRole('menuitem', { name: 'check-in' });
    expect(checkIn).toHaveAttribute('href', '/events/ev1/attendance');
  });

  it('hides check-in report when the event has not ended', async () => {
    vi.mocked(useFlag).mockReturnValue(true);
    renderMenu({ eventHasEnded: false });
    await openMenu();

    expect(screen.queryByRole('menuitem', { name: /check-in report/i })).not.toBeInTheDocument();
  });

  it('hides check-in report when the flag is off', async () => {
    vi.mocked(useFlag).mockReturnValue(false);
    renderMenu({ eventHasEnded: true });
    await openMenu();

    expect(screen.queryByRole('menuitem', { name: /check-in report/i })).not.toBeInTheDocument();
  });

  it('shows check-in report when the event ended and the flag is on', async () => {
    vi.mocked(useFlag).mockReturnValue(true);
    renderMenu({ eventHasEnded: true });
    await openMenu();

    const reportLink = screen.getByRole('menuitem', { name: 'check-in report' });
    expect(reportLink).toHaveAttribute('href', '/events/ev1/report');
  });

  it('shows "manage rsvps" for a host on a future event', async () => {
    vi.mocked(useFlag).mockReturnValue(false);
    renderMenu({ eventHasEnded: false, canManageRsvps: true });
    await openMenu();

    const manageRsvps = screen.getByRole('menuitem', { name: /manage rsvps/i });
    expect(manageRsvps).toHaveAttribute('href', '/events/ev1/manage-rsvps');
  });

  it('hides "manage rsvps" once the event has ended', async () => {
    vi.mocked(useFlag).mockReturnValue(false);
    renderMenu({ eventHasEnded: true, canManageRsvps: true });
    await openMenu();

    expect(screen.queryByRole('menuitem', { name: /manage rsvps/i })).not.toBeInTheDocument();
  });

  it('hides "manage rsvps" when the viewer cannot manage rsvps', async () => {
    vi.mocked(useFlag).mockReturnValue(false);
    renderMenu({ eventHasEnded: false, canManageRsvps: false });
    await openMenu();

    expect(screen.queryByRole('menuitem', { name: /manage rsvps/i })).not.toBeInTheDocument();
  });

  it('shows email blast and group text for a published event with guests', async () => {
    vi.mocked(useFlag).mockReturnValue(false);
    renderMenu();
    await openMenu();

    expect(screen.getByRole('menuitem', { name: 'email blast' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'group text' })).toBeInTheDocument();
  });

  it('hides email blast for a draft event but keeps group text', async () => {
    vi.mocked(useFlag).mockReturnValue(false);
    renderMenu({ event: { status: EventStatus.Draft } });
    await openMenu();

    expect(screen.queryByRole('menuitem', { name: 'email blast' })).not.toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'group text' })).toBeInTheDocument();
  });

  it('hides email blast when there are no guests', async () => {
    vi.mocked(useFlag).mockReturnValue(false);
    renderMenu({ event: { guests: [] } });
    await openMenu();

    expect(screen.queryByRole('menuitem', { name: 'email blast' })).not.toBeInTheDocument();
  });
});
