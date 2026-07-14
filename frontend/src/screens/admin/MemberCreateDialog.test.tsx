import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useCreateUser } from '@/api/users';

import { MemberCreateDialog } from './MemberCreateDialog';

vi.mock('@/api/users', () => ({
  useCreateUser: vi.fn(),
}));

describe('MemberCreateDialog', () => {
  const mutateAsync = vi.fn();

  beforeEach(() => {
    mutateAsync.mockReset();
    mutateAsync.mockResolvedValue({
      id: '1',
      phoneNumber: '+12025550101',
      fullName: '',
      firstName: '',
      magicLinkToken: 'tok',
    });
    vi.mocked(useCreateUser).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateUser>);
  });

  it('renders email field with nudge copy', () => {
    render(<MemberCreateDialog open onClose={() => {}} />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByText(/asked for one at first login/i)).toBeInTheDocument();
  });

  it('does not submit when first name is blank', async () => {
    render(<MemberCreateDialog open onClose={() => {}} />);
    fireEvent.change(screen.getByLabelText(/phone number/i), { target: { value: '+12025550101' } });
    await userEvent.click(screen.getByRole('button', { name: /^create$/i }));
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it('submits with first name and no last name / email when left blank', async () => {
    render(<MemberCreateDialog open onClose={() => {}} />);
    await userEvent.type(screen.getByLabelText(/first name/i), 'Ada');
    fireEvent.change(screen.getByLabelText(/phone number/i), { target: { value: '+12025550101' } });
    await userEvent.click(screen.getByRole('button', { name: /^create$/i }));
    expect(mutateAsync).toHaveBeenCalledWith({
      phoneNumber: '+12025550101',
      firstName: 'Ada',
    });
  });

  it('submits with last name and email when filled', async () => {
    render(<MemberCreateDialog open onClose={() => {}} />);
    await userEvent.type(screen.getByLabelText(/first name/i), 'Ada');
    await userEvent.type(screen.getByLabelText(/last name/i), 'Lovelace');
    fireEvent.change(screen.getByLabelText(/phone number/i), { target: { value: '+12025550101' } });
    await userEvent.type(screen.getByLabelText(/email/i), 'new@example.com');
    await userEvent.click(screen.getByRole('button', { name: /^create$/i }));
    expect(mutateAsync).toHaveBeenCalledWith({
      phoneNumber: '+12025550101',
      firstName: 'Ada',
      lastName: 'Lovelace',
      email: 'new@example.com',
    });
  });
});
