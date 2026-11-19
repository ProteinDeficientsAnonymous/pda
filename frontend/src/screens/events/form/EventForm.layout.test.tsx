import { describe, expect, it, vi } from 'vitest';

import type * as EventWritesModule from '@/api/eventWrites';
import { useAuthStore } from '@/auth/store';
import { makeUser } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

type EventWrites = typeof EventWritesModule;

vi.mock('@/api/eventWrites', async () => {
  const actual = await vi.importActual<EventWrites>('@/api/eventWrites');
  return {
    ...actual,
    useCreateEvent: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUpdateEvent: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUploadEventPhoto: () => ({ mutateAsync: vi.fn(), isPending: false }),
  };
});

vi.mock('./EventFormPhoto', () => ({ EventFormPhoto: () => null }));

import { EventForm } from './EventForm';

describe('EventForm layout', () => {
  it('fields column has min-w-0', () => {
    useAuthStore.setState({ user: makeUser(), status: 'authed' });
    const { container } = renderWithProviders(<EventForm />);
    const form = container.querySelector('form');
    const fields = form?.querySelector(':scope > div:nth-child(2)');
    expect(fields).toHaveClass('min-w-0');
  });
});
