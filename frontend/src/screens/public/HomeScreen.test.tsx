import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
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

import HomeScreen from './HomeScreen';
import { useHome } from '@/api/content';

const mockUseHome = vi.mocked(useHome);

const baseHomeData = {
  content: '',
  contentPm: '',
  contentHtml: '<p>Welcome</p>',
  joinContent: '',
  joinContentPm: '',
  joinContentHtml: '<p>Join us!</p>',
  donateUrl: 'https://example.com/donate',
  updatedAt: '2024-01-01T00:00:00Z',
};

const baseUser: User = {
  id: '1',
  phoneNumber: '+15551234567',
  displayName: 'Test User',
  email: 'test@example.com',
  bio: '',
  isSuperuser: false,
  isStaff: false,
  needsOnboarding: false,
  showPhone: false,
  showEmail: false,
  weekStart: 'monday',
  profilePhotoUrl: '',
  photoUpdatedAt: null,
  roles: [],
};

function renderWith(component: React.ReactElement) {
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

  it('shows join CTA for unauthenticated user', () => {
    useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
    mockUseHome.mockReturnValue({
      isPending: false,
      isError: false,
      data: { ...baseHomeData, joinContentHtml: '<p>Join us!</p>' },
    } as ReturnType<typeof useHome>);

    renderWith(<HomeScreen />);

    expect(screen.getByRole('link', { name: /request to join/i })).toBeInTheDocument();
  });

  it('hides join CTA for authenticated user', () => {
    useAuthStore.setState({ status: 'authed', user: baseUser, accessToken: 'token' });
    mockUseHome.mockReturnValue({
      isPending: false,
      isError: false,
      data: { ...baseHomeData, joinContentHtml: '<p>Join us!</p>' },
    } as ReturnType<typeof useHome>);

    renderWith(<HomeScreen />);

    expect(screen.queryByRole('link', { name: /request to join/i })).not.toBeInTheDocument();
  });

  it('shows donate button when donateUrl is non-empty', () => {
    mockUseHome.mockReturnValue({
      isPending: false,
      isError: false,
      data: { ...baseHomeData, donateUrl: 'https://example.com/donate' },
    } as ReturnType<typeof useHome>);

    renderWith(<HomeScreen />);

    expect(screen.getByRole('link', { name: /donate/i })).toBeInTheDocument();
  });

  it('hides donate button when donateUrl is empty string', () => {
    mockUseHome.mockReturnValue({
      isPending: false,
      isError: false,
      data: { ...baseHomeData, donateUrl: '' },
    } as ReturnType<typeof useHome>);

    renderWith(<HomeScreen />);

    expect(screen.queryByRole('link', { name: /donate/i })).not.toBeInTheDocument();
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
      data: { ...baseHomeData, joinContentHtml: '' },
    } as ReturnType<typeof useHome>);

    renderWith(<HomeScreen />);

    expect(screen.getAllByRole('button', { name: /edit/i }).length).toBeGreaterThan(0);
  });
});
