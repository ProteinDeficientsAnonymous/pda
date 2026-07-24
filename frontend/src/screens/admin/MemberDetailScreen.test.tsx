import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useRoles } from '@/api/roles';
import {
  type Member,
  useArchiveUser,
  useSendMemberMagicLink,
  useUpdateMemberRoles,
  useUpdateUser,
  useUsers,
} from '@/api/users';
import { useAuthStore } from '@/auth/store';

import MemberDetailScreen from './MemberDetailScreen';

vi.mock('@/api/users', () => ({
  useUsers: vi.fn(),
  useArchiveUser: vi.fn(),
  useSendMemberMagicLink: vi.fn(),
  useUpdateMemberRoles: vi.fn(),
  useUpdateUser: vi.fn(),
}));

vi.mock('@/api/roles', () => ({
  useRoles: vi.fn(),
}));

const member: Member = {
  id: 'member-1',
  fullName: 'ada lovelace',
  firstName: 'ada',
  lastName: 'lovelace',
  phoneNumber: '+12025550101',
  email: 'ada@example.com',
  bio: '',
  profilePhotoUrl: '',
  showPhone: true,
  showEmail: true,
  isMember: true,
  isSuperuser: false,
  isPaused: false,
  needsOnboarding: false,
  loginLinkRequested: false,
  lastAttendedAt: null,
  roles: [],
};

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={['/admin/members/member-1']}>
      <Routes>
        <Route path="/admin/members/:id" element={<MemberDetailScreen />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('MemberDetailScreen edit form', () => {
  const updateMutateAsync = vi.fn();

  beforeEach(() => {
    updateMutateAsync.mockReset();
    updateMutateAsync.mockResolvedValue(member);

    vi.mocked(useUsers).mockReturnValue({
      data: [member],
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useUsers>);

    vi.mocked(useRoles).mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useRoles>);

    vi.mocked(useArchiveUser).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useArchiveUser>);

    vi.mocked(useSendMemberMagicLink).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useSendMemberMagicLink>);

    vi.mocked(useUpdateMemberRoles).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useUpdateMemberRoles>);

    vi.mocked(useUpdateUser).mockReturnValue({
      mutateAsync: updateMutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useUpdateUser>);
  });

  it('shows separate first/last name fields prefilled from the member', async () => {
    renderScreen();
    await userEvent.click(screen.getByRole('button', { name: /^edit$/i }));
    expect(screen.getByLabelText(/^first name$/i)).toHaveValue('ada');
    expect(screen.getByLabelText(/last name/i)).toHaveValue('lovelace');
  });

  it('submits changed first/last name as first_name/last_name', async () => {
    renderScreen();
    await userEvent.click(screen.getByRole('button', { name: /^edit$/i }));

    const firstNameField = screen.getByLabelText(/^first name$/i);
    const lastNameField = screen.getByLabelText(/last name/i);
    await userEvent.clear(firstNameField);
    await userEvent.type(firstNameField, 'grace');
    await userEvent.clear(lastNameField);
    await userEvent.type(lastNameField, 'hopper');

    await userEvent.click(screen.getByRole('button', { name: /^save$/i }));

    expect(updateMutateAsync).toHaveBeenCalledWith({
      firstName: 'grace',
      lastName: 'hopper',
    });
  });

  it('does not patch name fields when unchanged', async () => {
    renderScreen();
    await userEvent.click(screen.getByRole('button', { name: /^edit$/i }));
    await userEvent.click(screen.getByRole('button', { name: /^save$/i }));
    expect(updateMutateAsync).not.toHaveBeenCalledWith(
      expect.objectContaining({ firstName: expect.anything() }),
    );
  });
});

describe('MemberDetailScreen roles section permission gating', () => {
  afterEach(() => {
    useAuthStore.setState({ status: 'idle', user: null, accessToken: null });
  });

  beforeEach(() => {
    vi.mocked(useUsers).mockReturnValue({
      data: [member],
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useUsers>);

    vi.mocked(useRoles).mockReturnValue({
      data: [{ id: 'role-1', name: 'admin', isDefault: true, permissions: [], userCount: 1 }],
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useRoles>);

    vi.mocked(useArchiveUser).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useArchiveUser>);

    vi.mocked(useSendMemberMagicLink).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useSendMemberMagicLink>);

    vi.mocked(useUpdateMemberRoles).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useUpdateMemberRoles>);

    vi.mocked(useUpdateUser).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useUpdateUser>);
  });

  it('hides the role checkboxes from a user without manage_roles', () => {
    useAuthStore.setState({
      status: 'authed',
      user: { roles: [{ name: 'vetter', isDefault: false, permissions: ['manage_users'] }] },
    } as unknown as ReturnType<typeof useAuthStore.getState>);

    renderScreen();
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /save roles/i })).not.toBeInTheDocument();
  });

  it('shows editable role checkboxes to a user with manage_roles', () => {
    useAuthStore.setState({
      status: 'authed',
      user: { roles: [{ name: 'admin_full', isDefault: false, permissions: ['manage_roles'] }] },
    } as unknown as ReturnType<typeof useAuthStore.getState>);

    renderScreen();
    expect(screen.getByRole('checkbox')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /save roles/i })).toBeInTheDocument();
  });
});
