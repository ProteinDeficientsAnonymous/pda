import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RequestLoginLinkDialog } from './RequestLoginLinkDialog';
import { useRequestLoginLink } from '@/api/auth';

vi.mock('@/api/auth', () => ({
  useRequestLoginLink: vi.fn(),
}));

describe('RequestLoginLinkDialog', () => {
  const mutateAsync = vi.fn();

  beforeEach(() => {
    mutateAsync.mockReset();
    mutateAsync.mockResolvedValue(undefined);
    vi.mocked(useRequestLoginLink).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useRequestLoginLink>);
  });

  it('shows email delivery copy after success', async () => {
    render(<RequestLoginLinkDialog open onClose={() => {}} />);
    await userEvent.type(screen.getByLabelText(/phone number/i), '+12025550101');
    await userEvent.click(screen.getByRole('button', { name: /request link/i }));
    expect(
      await screen.findByText(/we sent a login link to the email on file/i),
    ).toBeInTheDocument();
  });

  it('does not show success copy before submission', () => {
    render(<RequestLoginLinkDialog open onClose={() => {}} />);
    expect(
      screen.queryByText(/we sent a login link to the email on file/i),
    ).not.toBeInTheDocument();
  });
});
