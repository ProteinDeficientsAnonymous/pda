import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { makeEvent } from '@/test/fixtures';

const submitMutate = vi.fn();
const checkPhoneMutate = vi.fn();
vi.mock('@/api/publicRsvp', () => ({
  useSubmitPublicRsvp: () => ({ mutateAsync: submitMutate, isPending: false }),
  useCheckPublicRsvpPhone: () => ({ mutateAsync: checkPhoneMutate, isPending: false }),
}));

import { PublicRsvpForm } from './PublicRsvpForm';

function renderForm(event = makeEvent(), onSuccess = vi.fn()) {
  return render(
    <MemoryRouter>
      <PublicRsvpForm event={event} onSuccess={onSuccess} />
    </MemoryRouter>,
  );
}

function fillPhoneStep(phone = '4155550123') {
  fireEvent.click(screen.getByRole('button', { name: "i'm going" }));
  fireEvent.change(screen.getByLabelText(/phone number/i), { target: { value: phone } });
  fireEvent.click(screen.getByRole('button', { name: 'continue' }));
}

async function fillRequired() {
  checkPhoneMutate.mockResolvedValue({ status: 'new' });
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
    checkPhoneMutate.mockResolvedValue({ status: 'new' });
    const { rerender } = renderForm(makeEvent({ allowPlusOnes: true }));
    fillPhoneStep();
    await waitFor(() => expect(screen.getByRole('switch')).toBeInTheDocument());
    expect(screen.getByText(/your \+1 must be vegan too/i)).toBeInTheDocument();
    rerender(
      <MemoryRouter>
        <PublicRsvpForm event={makeEvent({ allowPlusOnes: false })} onSuccess={vi.fn()} />
      </MemoryRouter>,
    );
    expect(screen.queryByRole('switch')).not.toBeInTheDocument();
    expect(screen.queryByText(/your \+1 must be vegan too/i)).not.toBeInTheDocument();
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
    checkPhoneMutate.mockResolvedValue({ status: 'new' });
    renderForm();
    fireEvent.click(screen.getByRole('button', { name: 'maybe' }));
    fireEvent.change(screen.getByLabelText(/phone number/i), {
      target: { value: '+14155550123' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'continue' }));
    await waitFor(() => expect(screen.getByLabelText('first name')).toBeInTheDocument());
    expect(screen.getByText('maybe')).toBeInTheDocument();
  });

  it('directs members to sign in instead of showing the contact form', async () => {
    checkPhoneMutate.mockResolvedValue({ status: 'member' });
    renderForm();
    fillPhoneStep();
    await screen.findByText(/looks like you already have an account/);
    expect(screen.getByRole('link', { name: 'sign in' })).toHaveAttribute('href', '/login');
    expect(screen.queryByLabelText('first name')).not.toBeInTheDocument();
  });

  it('shows a check-your-email message for existing non-members', async () => {
    checkPhoneMutate.mockResolvedValue({ status: 'non_member' });
    renderForm();
    fillPhoneStep();
    await screen.findByText(
      'we recognized your number — check your email for a link to manage your rsvp',
    );
    expect(screen.queryByLabelText('first name')).not.toBeInTheDocument();
  });

  it('lets you change the status and go back to step one from the details step', async () => {
    checkPhoneMutate.mockResolvedValue({ status: 'new' });
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
    checkPhoneMutate.mockResolvedValue({ status: 'new' });
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

  it('shows join the waitlist instead of going when the event is at capacity', () => {
    renderForm(makeEvent({ maxAttendees: 2, attendingCount: 2 }));
    expect(screen.getByRole('button', { name: 'join the waitlist' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: "i'm going" })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'maybe' })).toBeInTheDocument();
  });

  it('submits attending status and shows join the waitlist copy when at capacity', async () => {
    checkPhoneMutate.mockResolvedValue({ status: 'new' });
    submitMutate.mockResolvedValue({
      event: { id: 'ev1' },
      rsvp: { status: 'waitlisted', has_plus_one: false },
    });
    const onSuccess = vi.fn();
    renderForm(makeEvent({ maxAttendees: 2, attendingCount: 2 }), onSuccess);
    fireEvent.click(screen.getByRole('button', { name: 'join the waitlist' }));
    fireEvent.change(screen.getByLabelText(/phone number/i), {
      target: { value: '+14155550123' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'continue' }));
    await waitFor(() => expect(screen.getByLabelText('first name')).toBeInTheDocument());
    expect(screen.getByText('join the waitlist')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('first name'), { target: { value: 'Ada' } });
    fireEvent.change(screen.getByLabelText('email'), { target: { value: 'ada@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: 'rsvp' }));
    await waitFor(() => expect(submitMutate).toHaveBeenCalled());
    expect(submitMutate).toHaveBeenCalledWith({
      eventId: 'ev1',
      payload: expect.objectContaining({ status: 'attending' }),
    });
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
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
    checkPhoneMutate.mockResolvedValue({ status: 'new' });
    renderForm();
    fillPhoneStep();
    await waitFor(() => expect(screen.getByLabelText('first name')).toBeInTheDocument());
    const hp = screen.getByLabelText('website (leave blank)');
    expect(hp).toHaveAttribute('name', 'website');
    expect(hp).toHaveAttribute('tabindex', '-1');
  });

  it('renders the comment field in step two', async () => {
    checkPhoneMutate.mockResolvedValue({ status: 'new' });

    renderForm();

    fillPhoneStep();

    expect(await screen.findByLabelText('comment (optional)')).toBeInTheDocument();
  });

  it('includes a non-empty comment in the submitted payload', async () => {
    const onSuccess = vi.fn();

    renderForm(makeEvent(), onSuccess);

    await fillRequired();

    fireEvent.change(screen.getByLabelText('comment (optional)'), {
      target: { value: 'bringing snacks' },
    });

    fireEvent.click(screen.getByRole('button', { name: 'rsvp' }));

    await waitFor(() => expect(submitMutate).toHaveBeenCalled());

    expect(submitMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        payload: expect.objectContaining({
          comment: 'bringing snacks',
        }),
      }),
    );
  });

  it('omits comment from payload when the field is blank', async () => {
    const onSuccess = vi.fn();

    renderForm(makeEvent(), onSuccess);

    await fillRequired();

    fireEvent.click(screen.getByRole('button', { name: 'rsvp' }));

    await waitFor(() => expect(submitMutate).toHaveBeenCalled());

    expect(submitMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        payload: expect.objectContaining({
          comment: null,
        }),
      }),
    );
  });
});
