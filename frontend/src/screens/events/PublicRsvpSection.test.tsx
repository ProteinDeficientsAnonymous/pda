import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type * as RouterDom from 'react-router-dom';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { canPublicRsvp, EventStatus, EventType, EventVisibility } from '@/models/event';
import { makeEvent } from '@/test/fixtures';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importActual) => {
  const actual = await importActual<typeof RouterDom>();
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockSubmit = vi.fn();
const mockCheckPhone = vi.fn();
vi.mock('@/api/publicRsvp', () => ({
  useSubmitPublicRsvp: () => ({ mutateAsync: mockSubmit, isPending: false }),
  useCheckPublicRsvpPhone: () => ({ mutateAsync: mockCheckPhone, isPending: false }),
}));

import { PublicRsvpSection } from './PublicRsvpSection';

function officialEvent(overrides: Partial<Parameters<typeof makeEvent>[0]> = {}) {
  return makeEvent({
    eventType: EventType.Official,
    visibility: EventVisibility.Public,
    ...overrides,
  });
}

describe('canPublicRsvp', () => {
  it('is true for official + public + rsvpEnabled + active + not-past', () => {
    expect(canPublicRsvp(officialEvent())).toBe(true);
  });
  it('is false for community events', () => {
    expect(canPublicRsvp(officialEvent({ eventType: EventType.Community }))).toBe(false);
  });
  it('is false for members-only visibility', () => {
    expect(canPublicRsvp(officialEvent({ visibility: EventVisibility.MembersOnly }))).toBe(false);
  });
  it('is false when rsvp disabled', () => {
    expect(canPublicRsvp(officialEvent({ rsvpEnabled: false }))).toBe(false);
  });
  it('is false when cancelled', () => {
    expect(canPublicRsvp(officialEvent({ status: EventStatus.Cancelled }))).toBe(false);
  });
  it('is false when past', () => {
    expect(canPublicRsvp(officialEvent({ isPast: true }))).toBe(false);
  });
});

describe('PublicRsvpSection', () => {
  beforeEach(() => {
    mockSubmit.mockReset();
    mockCheckPhone.mockReset();
    localStorage.clear();
  });

  it('renders the form heading initially', () => {
    render(
      <MemoryRouter>
        <PublicRsvpSection event={officialEvent()} />
      </MemoryRouter>,
    );
    expect(screen.getByRole('heading', { name: 'rsvp' })).toBeInTheDocument();
  });

  it('persists the rsvp token and refreshes without putting it in the url', async () => {
    mockCheckPhone.mockResolvedValue({ status: 'new', rsvp_token: '' });
    mockSubmit.mockResolvedValue({
      event: officialEvent(),
      rsvp: { status: 'attending', has_plus_one: false },
      rsvp_token: 'tok-abc',
    });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <PublicRsvpSection event={officialEvent({ id: 'evt-1' })} />
      </MemoryRouter>,
    );

    await user.click(screen.getByRole('button', { name: "i'm going" }));
    await user.type(screen.getByLabelText(/phone number/i), '4155550123');
    await user.click(screen.getByRole('button', { name: 'continue' }));
    await screen.findByLabelText(/first name/i);
    await user.type(screen.getByLabelText(/first name/i), 'Sam');
    await user.type(screen.getByLabelText(/^email/i), 'sam@example.com');
    await user.click(screen.getByRole('button', { name: 'rsvp' }));

    expect(mockNavigate).toHaveBeenCalledWith(0);
    expect(localStorage.getItem('pda-rsvp-token')).toBe('tok-abc');
  });

  it('prompts sign-in when the phone belongs to a member, without showing the form', async () => {
    mockCheckPhone.mockResolvedValue({ status: 'member', rsvp_token: '' });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <PublicRsvpSection event={officialEvent({ id: 'evt-1' })} />
      </MemoryRouter>,
    );

    await user.click(screen.getByRole('button', { name: "i'm going" }));
    await user.type(screen.getByLabelText(/phone number/i), '4155550123');
    await user.click(screen.getByRole('button', { name: 'continue' }));

    expect(await screen.findByRole('link', { name: 'sign in' })).toHaveAttribute('href', '/login');
    expect(screen.queryByLabelText(/first name/i)).not.toBeInTheDocument();
  });

  it('shows a check-your-email message when already rsvpd, without leaking a token', async () => {
    mockCheckPhone.mockResolvedValue({ status: 'already_rsvpd', rsvp_token: '' });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <PublicRsvpSection event={officialEvent({ id: 'evt-1' })} />
      </MemoryRouter>,
    );

    await user.click(screen.getByRole('button', { name: "i'm going" }));
    await user.type(screen.getByLabelText(/phone number/i), '4155550123');
    await user.click(screen.getByRole('button', { name: 'continue' }));

    await screen.findByText(
      'we recognized your number — check your email for a link to confirm your rsvp',
    );
    expect(mockSubmit).not.toHaveBeenCalled();
    expect(localStorage.getItem('pda-rsvp-token')).toBeNull();
  });
});
