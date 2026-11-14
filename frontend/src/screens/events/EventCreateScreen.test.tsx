import { screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { PlanningSlot } from '@/api/planning';
import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';
import { Permission } from '@/models/permissions';
import { makeEvent, makeUserWithPermissions } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import EventCreateScreen from './EventCreateScreen';

interface FormProps {
  initial?: { title?: string; eventType?: string; startDatetime?: string | null };
  onCreated?: (event: Event) => Promise<void>;
}

const { formProps, linkSlotEvent, toastError } = vi.hoisted(() => ({
  formProps: vi.fn<(p: FormProps) => void>(),
  linkSlotEvent: vi.fn(),
  toastError: vi.fn(),
}));

const slot: PlanningSlot = {
  id: 's1',
  label: 'march',
  month: 3,
  kind: 'monthly',
  order: 3,
  eventId: null,
  eventSlug: null,
  eventStatus: null,
};

vi.mock('sonner', () => ({ toast: { error: toastError } }));
let slotsState: { data?: PlanningSlot[]; isPending: boolean; isError: boolean };

vi.mock('@/api/planning', () => ({
  linkSlotEvent,
  usePlanningSlots: () => slotsState,
}));
vi.mock('./form/EventForm', () => ({
  EventForm: (p: FormProps) => {
    formProps(p);
    return <p>event form</p>;
  },
}));

function lastProps(): FormProps {
  return formProps.mock.calls.at(-1)?.[0] ?? {};
}

beforeEach(() => {
  vi.clearAllMocks();
  slotsState = { data: [slot], isPending: false, isError: false };
  linkSlotEvent.mockResolvedValue(slot);
  useAuthStore.setState({
    user: makeUserWithPermissions([Permission.TagOfficialEvent]),
    status: 'authed',
  });
});

afterEach(() => {
  vi.useRealTimers();
});

describe('EventCreateScreen', () => {
  it('renders a plain form without a planning slot', () => {
    renderWithProviders(<EventCreateScreen />, { route: '/events/add' });
    expect(lastProps().initial).toBeUndefined();
    expect(lastProps().onCreated).toBeUndefined();
  });

  it('prefills the form from the planning slot', async () => {
    renderWithProviders(<EventCreateScreen />, { route: '/events/add?planningSlot=s1&year=2027' });
    await screen.findByText('event form');
    const { initial } = lastProps();
    expect(initial?.title).toBe('march');
    expect(initial?.eventType).toBe('official');
    expect(initial?.startDatetime).toBe(new Date(2027, 2, 1, 10, 0).toISOString());
  });

  it('starts tomorrow when the slot month has already begun', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2027, 2, 15, 18, 30));
    renderWithProviders(<EventCreateScreen />, { route: '/events/add?planningSlot=s1&year=2027' });
    await screen.findByText('event form');
    expect(lastProps().initial?.startDatetime).toBe(new Date(2027, 2, 16, 10, 0).toISOString());
  });

  it('shows loading while the slot loads', () => {
    slotsState = { isPending: true, isError: false };
    renderWithProviders(<EventCreateScreen />, { route: '/events/add?planningSlot=s1&year=2027' });
    expect(screen.getByText('loading…')).toBeInTheDocument();
    expect(screen.queryByText('event form')).not.toBeInTheDocument();
  });

  it.each([
    ['the slot fails to load', { isPending: false, isError: true }],
    ['the slot is gone', { data: [], isPending: false, isError: false }],
  ])('shows an error instead of an unlinked form when %s', (_name, state) => {
    slotsState = state;
    renderWithProviders(<EventCreateScreen />, { route: '/events/add?planningSlot=s1&year=2027' });
    expect(screen.getByRole('alert')).toHaveTextContent(
      "couldn't load that planning slot — try again from the planning page",
    );
    expect(screen.queryByText('event form')).not.toBeInTheDocument();
  });

  it('keeps the event type open without the official-event permission', async () => {
    useAuthStore.setState({ user: makeUserWithPermissions([]), status: 'authed' });
    renderWithProviders(<EventCreateScreen />, { route: '/events/add?planningSlot=s1&year=2027' });
    await screen.findByText('event form');
    expect(lastProps().initial?.eventType).toBeUndefined();
  });

  it('links the created event to the slot', async () => {
    const { qc } = renderWithProviders(<EventCreateScreen />, {
      route: '/events/add?planningSlot=s1&year=2027',
    });
    const invalidate = vi.spyOn(qc, 'invalidateQueries');
    await screen.findByText('event form');
    await lastProps().onCreated?.(makeEvent({ id: 'e1' }));
    expect(linkSlotEvent).toHaveBeenCalledWith('s1', 'e1');
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['planning'] });
    expect(toastError).not.toHaveBeenCalled();
  });

  it('toasts instead of throwing when linking fails', async () => {
    linkSlotEvent.mockRejectedValue(new Error('nope'));
    renderWithProviders(<EventCreateScreen />, { route: '/events/add?planningSlot=s1&year=2027' });
    await screen.findByText('event form');
    await lastProps().onCreated?.(makeEvent({ id: 'e1' }));
    await waitFor(() => {
      expect(toastError).toHaveBeenCalledWith(
        "event saved, but couldn't link it to the planning slot",
      );
    });
  });
});
