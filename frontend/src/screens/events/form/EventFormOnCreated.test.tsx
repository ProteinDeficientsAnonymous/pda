import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type * as ReactRouterDom from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import type * as EventWritesModule from '@/api/eventWrites';
import { makeEvent } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

const { createEvent, navigate } = vi.hoisted(() => ({ createEvent: vi.fn(), navigate: vi.fn() }));

vi.mock('react-router-dom', async (importOriginal) => ({
  ...(await importOriginal<typeof ReactRouterDom>()),
  useNavigate: () => navigate,
}));
vi.mock('@/api/eventWrites', async (importActual) => ({
  ...(await importActual<typeof EventWritesModule>()),
  useCreateEvent: () => ({ mutateAsync: createEvent, isPending: false }),
}));
vi.mock('@/api/eventTags', () => ({ useEventTags: () => ({ data: [], isPending: false }) }));
vi.mock('./EventFormPhoto', () => ({ EventFormPhoto: () => null }));

import { EventForm } from './EventForm';

describe('EventForm onCreated', () => {
  it('runs after the event is created and before navigating to it', async () => {
    const created = makeEvent({ id: 'e1', slug: 'march' });
    createEvent.mockResolvedValue(created);
    const onCreated = vi.fn(async () => {});
    const start = new Date(2099, 2, 1, 10).toISOString();
    renderWithProviders(
      <EventForm initial={{ title: 'march', startDatetime: start }} onCreated={onCreated} />,
    );

    await userEvent.click(screen.getByRole('button', { name: 'publish' }));

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/events/march');
    });
    expect(onCreated).toHaveBeenCalledWith(created);
    const [createOrder] = createEvent.mock.invocationCallOrder;
    const [linkOrder] = onCreated.mock.invocationCallOrder;
    const [navigateOrder] = navigate.mock.invocationCallOrder;
    expect(createOrder).toBeLessThan(linkOrder ?? 0);
    expect(linkOrder).toBeLessThan(navigateOrder ?? 0);
  });
});
