import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  type Event,
  EventStatus,
  EventType,
  EventVisibility,
  InvitePermission,
} from '@/models/event';

const submitMutate = vi.fn();
const checkPhoneMutate = vi.fn();
vi.mock('@/api/publicRsvp', () => ({
  useSubmitPublicRsvp: () => ({ mutateAsync: submitMutate, isPending: false }),
  useCheckPublicRsvpPhone: () => ({ mutateAsync: checkPhoneMutate, isPending: false }),
}));

import { PublicRsvpForm } from './PublicRsvpForm';

function makeEvent(overrides: Partial<Event> = {}): Event {
  return {
    id: 'ev1',
    title: 'Potluck',
    description: '',
    startDatetime: new Date('2099-06-01T18:00:00Z'),
    endDatetime: null,
    location: '',
    latitude: null,
    longitude: null,
    whatsappLink: '',
    partifulLink: '',
    otherLink: '',
    venmoLink: '',
    cashappLink: '',
    zelleInfo: '',
    price: '',
    rsvpEnabled: true,
    allowPlusOnes: true,
    maxAttendees: null,
    attendingCount: 0,
    waitlistedCount: 0,
    invitedCount: 0,
    datetimeTbd: false,
    hasPoll: false,
    datetimePollSlug: null,
    createdById: null,
    createdByName: null,
    createdByPhotoUrl: '',
    coHostIds: [],
    coHostNames: [],
    coHostPhotoUrls: [],
    coHostInviteIds: [],
    guests: [],
    myRsvp: null,
    viewerUserId: null,
    surveySlugs: [],
    invitedUserIds: [],
    invitedUserNames: [],
    invitedUserPhotoUrls: [],
    invitePermission: InvitePermission.AllMembers,
    pendingCohostInvites: [],
    myPendingCohostInviteId: null,
    eventType: EventType.Official,
    visibility: EventVisibility.Public,
    photoUrl: '',
    photoUpdatedAt: null,
    tags: [],
    isPast: false,
    status: EventStatus.Active,
    ...overrides,
  };
}

function renderForm(
  event = makeEvent(),
  onSuccess = vi.fn(),
  onMember = vi.fn(),
  onAlreadyRsvpd = vi.fn(),
) {
  return render(
    <MemoryRouter>
      <PublicRsvpForm
        event={event}
        onSuccess={onSuccess}
        onMember={onMember}
        onAlreadyRsvpd={onAlreadyRsvpd}
      />
    </MemoryRouter>,
  );
}

function fillPhoneStep(phone = '4155550123') {
  fireEvent.click(screen.getByRole('button', { name: "i'm going" }));
  fireEvent.change(screen.getByLabelText(/phone number/i), { target: { value: phone } });
  fireEvent.click(screen.getByRole('button', { name: 'continue' }));
}

async function fillRequired() {
  checkPhoneMutate.mockResolvedValue({ status: 'new', rsvp_token: '' });
  fillPhoneStep();
  await waitFor(() => expect(screen.getByLabelText('first name')).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText('first name'), { target: { value: 'Ada' } });
  fireEvent.change(screen.getByLabelText('email'), { target: { value: 'ada@example.com' } });
}

describe('PublicRsvpForm', () => {
  beforeEach(() => {
    submitMutate.mockReset();
    submitMutate.mockResolvedValue({
      event: { id: 'ev1' },
      rsvp: { status: 'attending', has_plus_one: false },
    });
    checkPhoneMutate.mockReset();
  });

  it('submits the correct payload shape', async () => {
    const onSuccess = vi.fn();
    renderForm(makeEvent(), onSuccess);
    await fillRequired();
    fireEvent.click(screen.getByRole('button', { name: 'rsvp' }));
    await waitFor(() => expect(submitMutate).toHaveBeenCalled());
    expect(submitMutate).toHaveBeenCalledWith({
      eventId: 'ev1',
      payload: expect.objectContaining({
        first_name: 'Ada',
        email: 'ada@example.com',
        phone_number: '+14155550123',
        status: 'attending',
        has_plus_one: false,
        website: '',
      }),
    });
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
  });

  it('renders the plus-one toggle only when allowPlusOnes', async () => {
    checkPhoneMutate.mockResolvedValue({ status: 'new', rsvp_token: '' });
    const { rerender } = renderForm(makeEvent({ allowPlusOnes: true }));
    fillPhoneStep();
    await waitFor(() => expect(screen.getByRole('switch')).toBeInTheDocument());
    rerender(
      <MemoryRouter>
        <PublicRsvpForm
          event={makeEvent({ allowPlusOnes: false })}
          onSuccess={vi.fn()}
          onMember={vi.fn()}
          onAlreadyRsvpd={vi.fn()}
        />
      </MemoryRouter>,
    );
    expect(screen.queryByRole('switch')).not.toBeInTheDocument();
  });

  it('shows only going/maybe status options in step one', () => {
    renderForm();
    expect(screen.getByRole('button', { name: "i'm going" })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'maybe' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: "can't go" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/phone number/i)).not.toBeInTheDocument();
  });

  it('advances to the phone step after picking a status', () => {
    renderForm();
    fireEvent.click(screen.getByRole('button', { name: 'maybe' }));
    expect(screen.getByLabelText(/phone number/i)).toBeInTheDocument();
  });

  it('advances to the contact-details step after the phone check resolves new', async () => {
    checkPhoneMutate.mockResolvedValue({ status: 'new', rsvp_token: '' });
    renderForm();
    fireEvent.click(screen.getByRole('button', { name: 'maybe' }));
    fireEvent.change(screen.getByLabelText(/phone number/i), {
      target: { value: '+14155550123' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'continue' }));
    await waitFor(() => expect(screen.getByLabelText('first name')).toBeInTheDocument());
    expect(screen.getByText('maybe')).toBeInTheDocument();
  });

  it('calls onMember when the phone belongs to a member', async () => {
    checkPhoneMutate.mockResolvedValue({ status: 'member', rsvp_token: '' });
    const onMember = vi.fn();
    renderForm(makeEvent(), vi.fn(), onMember);
    fillPhoneStep();
    await waitFor(() => expect(onMember).toHaveBeenCalled());
  });

  it('calls onAlreadyRsvpd with the refreshed token when already rsvpd', async () => {
    checkPhoneMutate.mockResolvedValue({ status: 'already_rsvpd', rsvp_token: 'tok-xyz' });
    const onAlreadyRsvpd = vi.fn();
    renderForm(makeEvent(), vi.fn(), vi.fn(), onAlreadyRsvpd);
    fillPhoneStep();
    await waitFor(() => expect(onAlreadyRsvpd).toHaveBeenCalledWith({ rsvpToken: 'tok-xyz' }));
  });

  it('shows a check-your-email message instead of the contact form when recognized', async () => {
    checkPhoneMutate.mockResolvedValue({ status: 'recognized', rsvp_token: '' });
    renderForm();
    fillPhoneStep();
    await screen.findByText(
      'we recognized your number — check your email for a link to confirm your rsvp',
    );
    expect(screen.queryByLabelText('first name')).not.toBeInTheDocument();
  });

  it('lets you change the status and go back to step one from the details step', async () => {
    checkPhoneMutate.mockResolvedValue({ status: 'new', rsvp_token: '' });
    renderForm();
    fireEvent.click(screen.getByRole('button', { name: 'maybe' }));
    fireEvent.change(screen.getByLabelText(/phone number/i), {
      target: { value: '+14155550123' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'continue' }));
    await waitFor(() => expect(screen.getByLabelText('first name')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: 'change' }));
    expect(screen.getByRole('button', { name: "i'm going" })).toBeInTheDocument();
    expect(screen.queryByLabelText('first name')).not.toBeInTheDocument();
  });

  it('submits maybe status chosen in step one', async () => {
    checkPhoneMutate.mockResolvedValue({ status: 'new', rsvp_token: '' });
    const onSuccess = vi.fn();
    renderForm(makeEvent(), onSuccess);
    fireEvent.click(screen.getByRole('button', { name: 'maybe' }));
    fireEvent.change(screen.getByLabelText(/phone number/i), {
      target: { value: '+14155550123' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'continue' }));
    await waitFor(() => expect(screen.getByLabelText('first name')).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText('first name'), { target: { value: 'Ada' } });
    fireEvent.change(screen.getByLabelText('email'), { target: { value: 'ada@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: 'rsvp' }));
    await waitFor(() => expect(submitMutate).toHaveBeenCalled());
    expect(submitMutate).toHaveBeenCalledWith({
      eventId: 'ev1',
      payload: expect.objectContaining({ status: 'maybe' }),
    });
  });

  it('shows a 409 inline error with a sign-in link', async () => {
    submitMutate.mockRejectedValue({ isAxiosError: true, response: { status: 409 } });
    renderForm();
    await fillRequired();
    fireEvent.click(screen.getByRole('button', { name: 'rsvp' }));
    await screen.findByText('looks like you already have an account — sign in to rsvp');
    expect(screen.getByRole('link', { name: 'sign in' })).toHaveAttribute('href', '/login');
  });

  it('shows a 429 rate-limit error', async () => {
    submitMutate.mockRejectedValue({ isAxiosError: true, response: { status: 429 } });
    renderForm();
    await fillRequired();
    fireEvent.click(screen.getByRole('button', { name: 'rsvp' }));
    await screen.findByText("you're rsvping too fast — try again in a few minutes");
  });

  it('renders the hidden honeypot field', async () => {
    checkPhoneMutate.mockResolvedValue({ status: 'new', rsvp_token: '' });
    renderForm();
    fillPhoneStep();
    await waitFor(() => expect(screen.getByLabelText('first name')).toBeInTheDocument());
    const hp = screen.getByLabelText('website (leave blank)');
    expect(hp).toHaveAttribute('name', 'website');
    expect(hp).toHaveAttribute('tabindex', '-1');
  });
});
