import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type * as EventWritesModule from '@/api/eventWrites';
import { useAuthStore } from '@/auth/store';
import { makeEvent, makeUser } from '@/test/fixtures';

type EventWrites = typeof EventWritesModule;

const { updateEvent } = vi.hoisted(() => ({ updateEvent: vi.fn() }));

vi.mock('@/api/eventWrites', async () => {
  const actual = await vi.importActual<EventWrites>('@/api/eventWrites');
  return {
    ...actual,
    useCreateEvent: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUpdateEvent: () => ({ mutateAsync: updateEvent, isPending: false }),
    useUploadEventPhoto: () => ({ mutateAsync: vi.fn(), isPending: false }),
  };
});

vi.mock('@/api/eventRsvpQuestions', () => ({ syncEventRsvpQuestions: vi.fn(async () => []) }));
vi.mock('./EventFormPhoto', () => ({ EventFormPhoto: () => null }));

import { EventForm } from './EventForm';

const existing = makeEvent({ id: 'evt-1', slug: 'potluck', createdById: 'host' });

function renderForm(event = existing) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/events/potluck/edit']}>
        <Routes>
          <Route path="/events/:id/edit" element={<EventForm existing={event} />} />
          <Route path="/events/:id" element={<p>detail page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('EventForm slug', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: makeUser({ id: 'host', fullName: 'host person', phoneNumber: '+15551110000' }),
      status: 'authed',
    });
  });

  it('is not shown on create', () => {
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <EventForm />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.queryByLabelText('event url')).not.toBeInTheDocument();
  });

  it('normalizes typed input into slug form', () => {
    renderForm();
    const field = screen.getByLabelText('event url');
    fireEvent.change(field, { target: { value: 'Summer Potluck!' } });
    expect(field).toHaveValue('summer-potluck');
  });

  it('sends a changed slug and lands on the new url', async () => {
    updateEvent.mockResolvedValue({ ...existing, slug: 'summer-potluck' });
    renderForm();
    fireEvent.change(screen.getByLabelText('event url'), { target: { value: 'summer-potluck' } });
    fireEvent.click(screen.getByRole('button', { name: 'save' }));

    await waitFor(() => {
      expect(updateEvent).toHaveBeenCalledWith(expect.objectContaining({ slug: 'summer-potluck' }));
    });
    expect(await screen.findByText('detail page')).toBeInTheDocument();
  });

  it('omits an unchanged slug from the patch', async () => {
    updateEvent.mockResolvedValue(existing);
    renderForm();
    fireEvent.click(screen.getByRole('button', { name: 'save' }));

    await waitFor(() => {
      expect(updateEvent).toHaveBeenCalled();
    });
    expect(updateEvent.mock.calls[0]![0]).not.toHaveProperty('slug');
  });
});
