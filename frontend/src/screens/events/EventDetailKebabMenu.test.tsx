import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

vi.mock('@/api/featureFlags', () => ({
  useFlag: vi.fn(),
}));

import { useFlag } from '@/api/featureFlags';

import { EventDetailKebabMenu } from './EventDetailKebabMenu';

function renderMenu(overrides: { eventHasEnded?: boolean; canManageRsvps?: boolean } = {}) {
  return render(
    <MemoryRouter>
      <EventDetailKebabMenu
        eventId="ev1"
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
});
