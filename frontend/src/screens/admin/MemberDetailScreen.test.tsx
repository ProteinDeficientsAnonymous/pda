import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useRoles } from '@/api/roles';
import {
  type Member,
  useArchiveUser,
  useMemberAttendedEvents,
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
  useMemberAttendedEvents: vi.fn(),
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
  hasJoinedWhatsapp: false,
  needsOnboarding: false,
  loginLinkRequested: false,
  lastAttendedAt: null,
  attendedCount: 0,
  dateJoined: new Date('2026-01-01T00:00:00Z'),
  roles: [],
};

function mockAttendedEvents(
  data: ReturnType<typeof useMemberAttendedEvents>['data'] = [],
  state: { isPending?: boolean; isError?: boolean } = {},
) {
  vi.mocked(useMemberAttendedEvents).mockReturnValue({
    data,
    isPending: state.isPending ?? false,
    isError: state.isError ?? false,
  } as unknown as ReturnType<typeof useMemberAttendedEvents>);
}

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
    mockAttendedEvents();
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

  it('toggles joined whatsapp directly from the detail page', async () => {
    renderScreen();
    await userEvent.click(screen.getByRole('switch', { name: /joined whatsapp/i }));
    expect(updateMutateAsync).toHaveBeenCalledWith({ hasJoinedWhatsapp: true });
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

describe('MemberDetailScreen roles section admin lock', () => {
  afterEach(() => {
    useAuthStore.setState({ status: 'idle', user: null, accessToken: null });
  });

  beforeEach(() => {
    mockAttendedEvents();
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

  it('shows editable role checkboxes to a non-admin user with manage_users', () => {
    useAuthStore.setState({
      status: 'authed',
      user: { roles: [{ name: 'super_vetter', isDefault: false, permissions: ['manage_users'] }] },
    } as unknown as ReturnType<typeof useAuthStore.getState>);

    renderScreen();
    expect(screen.getByRole('checkbox')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /save roles/i })).toBeInTheDocument();
  });

  it('shows editable role checkboxes to the built-in admin role', () => {
    useAuthStore.setState({
      status: 'authed',
      user: { roles: [{ name: 'admin', isDefault: true, permissions: [] }] },
    } as unknown as ReturnType<typeof useAuthStore.getState>);

    renderScreen();
    expect(screen.getByRole('checkbox')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /save roles/i })).toBeInTheDocument();
  });

  it('disables the admin checkbox for a manage_users holder who is not admin themself', () => {
    useAuthStore.setState({
      status: 'authed',
      user: { roles: [{ name: 'super_vetter', isDefault: false, permissions: ['manage_users'] }] },
    } as unknown as ReturnType<typeof useAuthStore.getState>);

    renderScreen();
    expect(screen.getByRole('checkbox')).toBeDisabled();
  });

  it('leaves the admin checkbox enabled for an admin user', () => {
    useAuthStore.setState({
      status: 'authed',
      user: { roles: [{ name: 'admin', isDefault: true, permissions: [] }] },
    } as unknown as ReturnType<typeof useAuthStore.getState>);

    renderScreen();
    expect(screen.getByRole('checkbox')).not.toBeDisabled();
  });
});

describe('MemberDetailScreen events attended', () => {
  beforeEach(() => {
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
    for (const hook of [
      useArchiveUser,
      useSendMemberMagicLink,
      useUpdateMemberRoles,
      useUpdateUser,
    ]) {
      vi.mocked(hook).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as never);
    }
  });

  it('lists attended events with a count and links to each event', () => {
    mockAttendedEvents([
      {
        eventId: 'e2',
        title: 'Potluck Picnic',
        startDatetime: new Date('2026-05-02T18:00:00Z'),
        eventType: 'official',
      },
      {
        eventId: 'e1',
        title: 'Book Club',
        startDatetime: new Date('2026-03-15T18:00:00Z'),
        eventType: 'community',
      },
    ]);

    renderScreen();

    expect(screen.getByRole('heading', { name: '2 events attended' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'potluck picnic' })).toHaveAttribute(
      'href',
      '/events/e2',
    );
    expect(screen.getByText(/mar 15, 2026 · community/)).toBeInTheDocument();
  });

  it('shows an empty state when the member never attended', () => {
    mockAttendedEvents([]);
    renderScreen();
    expect(screen.getByText('no events attended yet')).toBeInTheDocument();
  });

  it('shows an error message when the history fails to load', () => {
    mockAttendedEvents(undefined, { isError: true });
    renderScreen();
    expect(screen.getByText("couldn't load events attended")).toBeInTheDocument();
  });
});
