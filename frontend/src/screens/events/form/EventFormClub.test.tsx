import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Club } from '@/api/clubs';
import type * as EventWritesModule from '@/api/eventWrites';
import { useAuthStore } from '@/auth/store';
import { type Event, EventType } from '@/models/event';
import { Permission } from '@/models/permissions';
import { makeEvent, makeUser } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

const { createEvent, updateEvent, useClubs } = vi.hoisted(() => ({
  createEvent: vi.fn(),
  updateEvent: vi.fn(),
  useClubs: vi.fn(),
}));

vi.mock('@/api/clubs', () => ({ useClubs }));

vi.mock('@/api/eventWrites', async (importActual) => ({
  ...(await importActual<typeof EventWritesModule>()),
  useCreateEvent: () => ({ mutateAsync: createEvent, isPending: false }),
  useUpdateEvent: () => ({ mutateAsync: updateEvent, isPending: false }),
  useUploadEventPhoto: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock('@/api/eventTags', () => ({ useEventTags: () => ({ data: [], isPending: false }) }));
vi.mock('./EventFormPhoto', () => ({ EventFormPhoto: () => null }));

import { EventForm } from './EventForm';

const clubs: Club[] = [
  { id: 'c1', name: 'book club', requirements: '' },
  { id: 'c2', name: 'run club', requirements: '' },
];
const start = new Date(2099, 2, 1, 10).toISOString();

function renderForm({ existing, list = clubs }: { existing?: Event; list?: Club[] } = {}) {
  useAuthStore.setState({
    user: makeUser({
      roles: [
        { id: 'r1', name: 'planner', isDefault: false, permissions: [Permission.TagClubEvent] },
      ],
    }),
    status: 'authed',
  });
  useClubs.mockReturnValue({ data: list, isPending: false, isError: false });
  renderWithProviders(
    <EventForm
      existing={existing}
      initial={existing ? undefined : { title: 'x', startDatetime: start }}
    />,
  );
}

const clubToggle = () => screen.getByRole('switch', { name: 'make it a pda club event' });

describe('EventForm club dropdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows the dropdown only for club events', async () => {
    renderForm();
    expect(screen.queryByLabelText('which club?')).not.toBeInTheDocument();
    await userEvent.click(clubToggle());
    expect(screen.getByLabelText('which club?')).toHaveValue('');
    expect(screen.getByRole('option', { name: 'pick a club' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'run club' })).toBeInTheDocument();
    await userEvent.click(clubToggle());
    expect(screen.queryByLabelText('which club?')).not.toBeInTheDocument();
  });

  it('blocks saving a club event without a club', async () => {
    renderForm();
    await userEvent.click(clubToggle());
    await userEvent.click(screen.getByRole('button', { name: 'publish' }));
    expect(await screen.findByText('pick a club', { selector: 'p' })).toBeInTheDocument();
    expect(createEvent).not.toHaveBeenCalled();
  });

  it('sends the picked club on create', async () => {
    createEvent.mockResolvedValue(makeEvent({ slug: 'x' }));
    renderForm();
    await userEvent.click(clubToggle());
    await userEvent.selectOptions(screen.getByLabelText('which club?'), 'c2');
    await userEvent.click(screen.getByRole('button', { name: 'publish' }));
    await waitFor(() => {
      expect(createEvent).toHaveBeenCalledWith(
        expect.objectContaining({ eventType: EventType.Club, clubId: 'c2' }),
      );
    });
  });

  it('clears the club when the type changes away', async () => {
    renderForm();
    await userEvent.click(clubToggle());
    await userEvent.selectOptions(screen.getByLabelText('which club?'), 'c1');
    await userEvent.click(clubToggle());
    await userEvent.click(clubToggle());
    expect(screen.getByLabelText('which club?')).toHaveValue('');
  });

  it('points to admin when there are no clubs, and still blocks saving', async () => {
    renderForm({ list: [] });
    await userEvent.click(clubToggle());
    expect(screen.getByText('no clubs yet — add them in admin > clubs')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'publish' }));
    expect(await screen.findByText('pick a club')).toBeInTheDocument();
    expect(createEvent).not.toHaveBeenCalled();
  });

  describe('editing', () => {
    const existing = makeEvent({
      id: 'e1',
      slug: 'e1',
      eventType: EventType.Club,
      club: clubs[0] ?? null,
      startDatetime: new Date(start),
    });

    it('omits the club when it is unchanged', async () => {
      updateEvent.mockResolvedValue(existing);
      renderForm({ existing });
      expect(screen.getByLabelText('which club?')).toHaveValue('c1');
      await userEvent.click(screen.getByRole('button', { name: 'save' }));
      await waitFor(() => {
        expect(updateEvent).toHaveBeenCalled();
      });
      expect(updateEvent.mock.calls[0]?.[0]).not.toHaveProperty('clubId');
    });

    it('sends the club when it changed', async () => {
      updateEvent.mockResolvedValue(existing);
      renderForm({ existing });
      await userEvent.selectOptions(screen.getByLabelText('which club?'), 'c2');
      await userEvent.click(screen.getByRole('button', { name: 'save' }));
      await waitFor(() => {
        expect(updateEvent).toHaveBeenCalledWith(expect.objectContaining({ clubId: 'c2' }));
      });
    });
  });
});
