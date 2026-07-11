import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';

// Mock API before importing the screen
vi.mock('@/api/content', () => ({
  useHome: vi.fn(),
  useUpdateHome: vi.fn(() => ({ mutateAsync: vi.fn() })),
}));

// Mock the RichEditor — TipTap requires a DOM environment not available in jsdom
vi.mock('@/components/RichEditor/RichEditor', () => ({
  RichEditor: () => <div data-testid="rich-editor" />,
}));

import { useHome } from '@/api/content';

import HomeScreen from './HomeScreen';

const mockUseHome = vi.mocked(useHome);

const baseHomeData = {
  content: '',
  contentPm: '',
  contentHtml: '<p>Welcome</p>',
  updatedAt: '2024-01-01T00:00:00Z',
};

const baseUser: User = {
  id: '1',
  phoneNumber: '+15551234567',
  displayName: 'Test User',
  email: 'test@example.com',
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

describe('HomeScreen', () => {
  it('shows loading indicator while data is fetching', () => {
    mockUseHome.mockReturnValue({
      isPending: true,
      isError: false,
      data: undefined,
    } as ReturnType<typeof useHome>);

    renderWith(<HomeScreen />);

    expect(screen.getByText('loading…')).toBeInTheDocument();
  });

  it('shows edit button for user with edit_homepage permission', () => {
    const editorUser: User = {
      ...baseUser,
      roles: [
        {
          id: 'role-1',
          name: 'editor',
          isDefault: true,
          permissions: ['edit_homepage'],
        },
      ],
    };
    useAuthStore.setState({ status: 'authed', user: editorUser, accessToken: 'token' });
    mockUseHome.mockReturnValue({
      isPending: false,
      isError: false,
      data: baseHomeData,
    } as ReturnType<typeof useHome>);

    renderWith(<HomeScreen />);

    expect(screen.getAllByRole('button', { name: /edit/i }).length).toBeGreaterThan(0);
  });
});
