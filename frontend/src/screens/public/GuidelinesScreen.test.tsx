import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';

vi.mock('@/api/content', () => ({
  useGuidelines: vi.fn(),
  useUpdateGuidelines: vi.fn(() => ({ mutateAsync: vi.fn() })),
}));

vi.mock('@/components/RichEditor/RichEditor', () => ({
  RichEditor: () => <div data-testid="rich-editor" />,
}));

import { useGuidelines } from '@/api/content';

import GuidelinesScreen from './GuidelinesScreen';

const mockUseGuidelines = vi.mocked(useGuidelines);

const baseGuidelinesData = {
  content: '',
  contentPm: '',
  contentHtml: '<p>Community guidelines content</p>',
  updatedAt: '2024-01-01T00:00:00Z',
};

const baseUser: User = {
  id: '1',
  phoneNumber: '+15551234567',
  firstName: 'Test',
  lastName: 'User',
  fullName: 'Test User',
  nickname: '',
  email: 'test@example.com',
  bio: '',
  pronouns: '',
  birthday: null,
  isSuperuser: false,
  isStaff: false,
  needsOnboarding: false,
  needsPasswordReset: false,
  needsGuidelinesConsent: false,
  needsSmsConsent: false,
  needsContactPrivacyConsent: false,
  showPhone: false,
  showEmail: false,
  showBirthday: false,
  hideLastName: false,
  weekStart: 'monday',
  calendarFeedScope: 'all',
  profilePhotoUrl: '',
  photoUpdatedAt: null,
  roles: [],
};

function renderWith(component: ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{component}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
});

describe('GuidelinesScreen', () => {
  it('shows loading indicator while fetching', () => {
    mockUseGuidelines.mockReturnValue({
      isPending: true,
      isError: false,
      data: undefined,
    } as ReturnType<typeof useGuidelines>);

    renderWith(<GuidelinesScreen />);

    expect(screen.getByText('loading…')).toBeInTheDocument();
  });

  it('hides edit button for member without edit_guidelines permission', () => {
    const memberUser: User = {
      ...baseUser,
      roles: [{ id: 'role-1', name: 'member', isDefault: true, permissions: [] }],
    };
    useAuthStore.setState({ status: 'authed', user: memberUser, accessToken: 'token' });
    mockUseGuidelines.mockReturnValue({
      isPending: false,
      isError: false,
      data: baseGuidelinesData,
    } as ReturnType<typeof useGuidelines>);

    renderWith(<GuidelinesScreen />);

    expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument();
  });

  it('shows edit button for user with edit_guidelines permission', () => {
    const editorUser: User = {
      ...baseUser,
      roles: [
        {
          id: 'role-1',
          name: 'moderator',
          isDefault: true,
          permissions: ['edit_guidelines'],
        },
      ],
    };
    useAuthStore.setState({ status: 'authed', user: editorUser, accessToken: 'token' });
    mockUseGuidelines.mockReturnValue({
      isPending: false,
      isError: false,
      data: baseGuidelinesData,
    } as ReturnType<typeof useGuidelines>);

    renderWith(<GuidelinesScreen />);

    expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument();
  });
});
