import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useRequestLoginLink } from '@/api/auth';

import { RequestLoginLinkDialog } from './RequestLoginLinkDialog';

vi.mock('@/api/auth', () => ({
  useRequestLoginLink: vi.fn(),
}));

describe('RequestLoginLinkDialog', () => {
  const mutateAsync = vi.fn();

  beforeEach(() => {
    mutateAsync.mockReset();
    mutateAsync.mockResolvedValue({ detail: 'ok', delivery: 'email' });
    vi.mocked(useRequestLoginLink).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useRequestLoginLink>);
  });

  it('shows email delivery copy when backend reports email delivery', async () => {
    mutateAsync.mockResolvedValue({ detail: 'ok', delivery: 'email' });
    render(<RequestLoginLinkDialog open onClose={() => {}} />);
    await userEvent.type(screen.getByLabelText(/phone number/i), '+12025550101');
    await userEvent.click(screen.getByRole('button', { name: /request link/i }));
    expect(
      await screen.findByText(/we sent a login link to the email on file/i),
    ).toBeInTheDocument();
  });

  it('shows admin-follow-up copy when backend reports admin delivery', async () => {
    mutateAsync.mockResolvedValue({ detail: 'ok', delivery: 'admin' });
    render(<RequestLoginLinkDialog open onClose={() => {}} />);
    await userEvent.type(screen.getByLabelText(/phone number/i), '+12025550101');
    await userEvent.click(screen.getByRole('button', { name: /request link/i }));
    expect(
      await screen.findByText(/an admin will follow up with your login link/i),
    ).toBeInTheDocument();
  });

  it('shows a distinct cooldown warning that says no new link was sent', async () => {
    mutateAsync.mockResolvedValue({
      detail: 'ok',
      delivery: 'cooldown',
      retryAfterSeconds: 90,
    });
    render(<RequestLoginLinkDialog open onClose={() => {}} />);
    await userEvent.type(screen.getByLabelText(/phone number/i), '+12025550101');
    await userEvent.click(screen.getByRole('button', { name: /request link/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/didn't send a new link/i);
    // The countdown surfaces the remaining wait from retryAfterSeconds (1:30).
    expect(alert).toHaveTextContent(/1:30/);
  });

  it('does not show the success sprout on the cooldown warning', async () => {
    mutateAsync.mockResolvedValue({
      detail: 'ok',
      delivery: 'cooldown',
      retryAfterSeconds: 90,
    });
    render(<RequestLoginLinkDialog open onClose={() => {}} />);
    await userEvent.type(screen.getByLabelText(/phone number/i), '+12025550101');
    await userEvent.click(screen.getByRole('button', { name: /request link/i }));

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.queryByText(/🌱/)).not.toBeInTheDocument();
  });

  it('does not show success copy before submission', () => {
    render(<RequestLoginLinkDialog open onClose={() => {}} />);
    expect(
      screen.queryByText(/we sent a login link to the email on file/i),
    ).not.toBeInTheDocument();
  });
});
