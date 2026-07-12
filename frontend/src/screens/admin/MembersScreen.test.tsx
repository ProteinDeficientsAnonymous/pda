import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Member } from '@/api/users';
import { useAuthStore } from '@/auth/store';
import { Permission } from '@/models/permissions';
import type { User } from '@/models/user';

// Mock the users API module so we can drive loading / error / data states
// without hitting the network. useCreateUser is only pulled in transitively
// by MemberCreateDialog if it opens, but the default here is closed.
vi.mock('@/api/users', () => ({
  useUsers: vi.fn(),
  useCreateUser: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
    reset: vi.fn(),
  })),
}));

import { useUsers } from '@/api/users';

import MembersScreen from './MembersScreen';

const mockUseUsers = vi.mocked(useUsers);

const baseUser: User = {
  id: 'me',
  phoneNumber: '+15551230000',
  firstName: 'Admin',
  lastName: 'User',
  fullName: 'Admin User',
  nickname: '',
  email: 'admin@example.com',
  bio: '',
  pronouns: '',
  isSuperuser: false,
  isStaff: false,
  needsOnboarding: false,
  needsPasswordReset: false,
  needsGuidelinesConsent: false,
  needsSmsConsent: false,
  showPhone: false,
  showEmail: false,
  weekStart: 'monday',
  calendarFeedScope: 'all',
  profilePhotoUrl: '',
  photoUpdatedAt: null,
  roles: [],
};

function adminUser(permissions: string[] = [Permission.ManageUsers]): User {
  return {
    ...baseUser,
    roles: [
      {
        id: 'role-admin',
        name: 'admin',
        isDefault: true,
        permissions,
      },
    ],
  };
}

function makeMember(overrides: Partial<Member> = {}): Member {
  return {
    id: 'member-1',
    firstName: 'Ada',
    lastName: '',
    fullName: 'Ada',
    phoneNumber: '+15551230001',
    email: '',
    bio: '',
    profilePhotoUrl: '',
    showPhone: true,
    showEmail: true,
    isSuperuser: false,
    isPaused: false,
    needsOnboarding: false,
    loginLinkRequested: false,
    roles: [],
    ...overrides,
  };
}

function renderScreen() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <MembersScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockUsersResult(overrides: Partial<ReturnType<typeof useUsers>>) {
  mockUseUsers.mockReturnValue({
    isPending: false,
    isError: false,
    data: [],
    ...overrides,
  } as ReturnType<typeof useUsers>);
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({
    status: 'authed',
    user: adminUser(),
    accessToken: 'tok',
  });
});

describe('MembersScreen', () => {
  it('displays member display names from the users query', () => {
    mockUsersResult({
      data: [
        makeMember({ id: 'm1', firstName: 'Ada', lastName: 'Lovelace', fullName: 'Ada Lovelace' }),
        makeMember({
          id: 'm2',
          firstName: 'Grace',
          lastName: 'Hopper',
          fullName: 'Grace Hopper',
        }),
      ],
    });

    renderScreen();

    expect(screen.getByText('Ada Lovelace')).toBeInTheDocument();
    expect(screen.getByText('Grace Hopper')).toBeInTheDocument();
  });

  it('filters members by user id prefix when searching', async () => {
    mockUsersResult({
      data: [
        makeMember({
          id: 'abc12345-aaaa-bbbb-cccc-dddddddddddd',
          firstName: 'Ada',
          lastName: 'Lovelace',
          fullName: 'Ada Lovelace',
        }),
        makeMember({
          id: 'def67890-eeee-ffff-1111-222222222222',
          firstName: 'Grace',
          lastName: 'Hopper',
          fullName: 'Grace Hopper',
        }),
      ],
    });

    renderScreen();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/^search$/i), 'abc12');

    expect(screen.getByText('Ada Lovelace')).toBeInTheDocument();
    expect(screen.queryByText('Grace Hopper')).not.toBeInTheDocument();
  });

  it('shows the empty state when there are no members', () => {
    mockUsersResult({ data: [] });

    renderScreen();

    expect(screen.getByText(/no members yet/i)).toBeInTheDocument();
  });

  it('shows an error message when the query fails', () => {
    mockUsersResult({
      isPending: false,
      isError: true,
      data: undefined,
    });

    renderScreen();

    expect(screen.getByRole('alert')).toHaveTextContent(/couldn't load members/i);
  });

  it('shows a loading state while the users query is pending', () => {
    mockUsersResult({
      isPending: true,
      isError: false,
      data: undefined,
    });

    renderScreen();

    expect(screen.getByText('loading…')).toBeInTheDocument();
  });

  it('renders the add-member button for an admin viewer', () => {
    mockUsersResult({ data: [] });

    renderScreen();

    expect(screen.getByRole('button', { name: /add member/i })).toBeInTheDocument();
  });

  // TODO(tier3-mismatch): Flutter gated the add-member button on the
  // `manage_users` permission inside the screen. React's MembersScreen always
  // renders the button — permission gating is enforced at the route/admin-hub
  // level (see AdminHubScreen). Locking the current React behavior: the
  // button is always present when the screen renders.
  it('renders the add-member button even without manage_users permission (react gates at route level)', () => {
    useAuthStore.setState({
      status: 'authed',
      user: adminUser([]),
      accessToken: 'tok',
    });
    mockUsersResult({ data: [] });

    renderScreen();

    expect(screen.getByRole('button', { name: /add member/i })).toBeInTheDocument();
  });

  it('renders the Members/Roles tab switcher for users with manage_roles', () => {
    useAuthStore.setState({
      status: 'authed',
      user: adminUser([Permission.ManageUsers, Permission.ManageRoles]),
      accessToken: 'tok',
    });
    mockUsersResult({ data: [] });

    renderScreen();

    const group = screen.getByRole('radiogroup', { name: /members or roles/i });
    expect(group).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'members' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'roles' })).toBeInTheDocument();
  });

  it('hides the tab switcher when the user lacks manage_roles', () => {
    useAuthStore.setState({
      status: 'authed',
      user: {
        ...baseUser,
        roles: [
          {
            id: 'role-custom',
            name: 'vettor',
            isDefault: false,
            permissions: [Permission.ManageUsers],
          },
        ],
      },
      accessToken: 'tok',
    });
    mockUsersResult({ data: [] });

    renderScreen();

    expect(screen.queryByRole('radiogroup', { name: /members or roles/i })).not.toBeInTheDocument();
  });
});
