import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

import type { Event } from '@/models/event';
import { makeEvent } from '@/test/fixtures';

const checkPhoneMutate = vi.fn();
vi.mock('@/api/publicRsvp', () => ({
  useSubmitPublicRsvp: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useCheckPublicRsvpPhone: () => ({ mutateAsync: checkPhoneMutate, isPending: false }),
}));

import { PublicRsvpForm } from './PublicRsvpForm';

function renderForm(event: Event) {
  return render(
    <MemoryRouter>
      <PublicRsvpForm event={event} onSuccess={vi.fn()} />
    </MemoryRouter>,
  );
}

describe('public rsvp a11y', () => {
  it('form step one has no axe violations', async () => {
    const { container } = renderForm(makeEvent());
    const results = await axe(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(results).toHaveNoViolations();
  }, 15000);

  it('form step two (phone) has no axe violations', async () => {
    const { container } = renderForm(makeEvent());
    fireEvent.click(screen.getByRole('button', { name: "i'm going" }));
    const results = await axe(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(results).toHaveNoViolations();
  }, 15000);

  it('form step three (contact details) has no axe violations', async () => {
    checkPhoneMutate.mockResolvedValue({ status: 'new' });
    const { container } = renderForm(makeEvent());
    fireEvent.click(screen.getByRole('button', { name: "i'm going" }));
    fireEvent.change(screen.getByLabelText(/phone number/i), { target: { value: '+14155550123' } });
    fireEvent.click(screen.getByRole('button', { name: 'continue' }));
    await waitFor(() => expect(screen.getByLabelText('first name')).toBeInTheDocument());
    const results = await axe(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(results).toHaveNoViolations();
  }, 15000);
});
