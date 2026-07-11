import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { updateProfile } from '@/api/auth';
import { useAuthStore } from '@/auth/store';

import { RequireEmail } from './RequireEmail';

vi.mock('@/api/auth', () => ({
  updateProfile: vi.fn(),
}));

vi.mock('@/auth/store', () => ({
  useAuthStore: Object.assign(vi.fn(), { setState: vi.fn() }),
}));

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  authClient: { post: vi.fn() },
  setAuthBridge: vi.fn(),
}));

describe('RequireEmail', () => {
  beforeEach(() => {
    vi.mocked(updateProfile).mockReset();
    (useAuthStore as unknown as { setState: ReturnType<typeof vi.fn> }).setState.mockReset();
  });

  it('renders the blocking form', () => {
    render(<RequireEmail onSkip={() => {}} />);
    expect(screen.getByRole('heading', { name: /add your email/i })).toBeInTheDocument();
    expect(screen.getByLabelText('email')).toBeInTheDocument();
  });

  it('submits and clears modal on success', async () => {
    const returned = { email: 'foo@example.com' };
    vi.mocked(updateProfile).mockResolvedValue(returned as never);
    render(<RequireEmail onSkip={() => {}} />);
    await userEvent.type(screen.getByLabelText('email'), 'foo@example.com');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    expect(updateProfile).toHaveBeenCalledWith({ email: 'foo@example.com' });
    expect(
      (useAuthStore as unknown as { setState: ReturnType<typeof vi.fn> }).setState,
    ).toHaveBeenCalledWith({ user: expect.objectContaining({ email: 'foo@example.com' }) });
  });

  it('shows conflict error inline', async () => {
    vi.mocked(updateProfile).mockRejectedValue({
      isAxiosError: true,
      response: {
        status: 409,
        data: { detail: [{ code: 'email.already_exists', field: 'email' }] },
      },
    });
    render(<RequireEmail onSkip={() => {}} />);
    await userEvent.type(screen.getByLabelText('email'), 'taken@example.com');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    expect(await screen.findByText(/already on another account/i)).toBeInTheDocument();
  });

  it('shows malformed-email error inline', async () => {
    render(<RequireEmail onSkip={() => {}} />);
    await userEvent.type(screen.getByLabelText('email'), 'not-an-email');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    expect(await screen.findByText(/not a valid email/i)).toBeInTheDocument();
    expect(updateProfile).not.toHaveBeenCalled();
  });

  it('skips via the "not now" button without saving', async () => {
    const onSkip = vi.fn();
    render(<RequireEmail onSkip={onSkip} />);
    await userEvent.click(screen.getByRole('button', { name: /not now/i }));
    expect(onSkip).toHaveBeenCalledOnce();
    expect(updateProfile).not.toHaveBeenCalled();
  });

  it('does not skip on escape', async () => {
    const onSkip = vi.fn();
    render(<RequireEmail onSkip={onSkip} />);
    await userEvent.keyboard('{Escape}');
    expect(onSkip).not.toHaveBeenCalled();
  });
});
