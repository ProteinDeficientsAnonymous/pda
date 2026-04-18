import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';

vi.mock('@/api/content', () => ({
  useFaq: vi.fn(),
  useUpdateFaq: vi.fn(() => ({ mutateAsync: vi.fn() })),
}));

vi.mock('@/components/RichEditor/RichEditor', () => ({
  RichEditor: () => <div data-testid="rich-editor" />,
}));

import FaqScreen from './FaqScreen';
import { useFaq } from '@/api/content';

const mockUseFaq = vi.mocked(useFaq);

const baseFaqData = {
  content: '',
  contentPm: '',
  contentHtml: '<p>Frequently asked questions</p>',
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

describe('FaqScreen', () => {
  it('shows loading indicator while fetching', () => {
    mockUseFaq.mockReturnValue({
      isPending: true,
      isError: false,
      data: undefined,
    } as ReturnType<typeof useFaq>);

    renderWith(<FaqScreen />);

    expect(screen.getByText('loading…')).toBeInTheDocument();
  });

  it('hides edit button for member without edit_faq permission', () => {
    const memberUser: User = {
      ...baseUser,
      roles: [{ id: 'role-1', name: 'member', isDefault: true, permissions: [] }],
    };
    useAuthStore.setState({ status: 'authed', user: memberUser, accessToken: 'token' });
    mockUseFaq.mockReturnValue({
      isPending: false,
      isError: false,
      data: baseFaqData,
    } as ReturnType<typeof useFaq>);

    renderWith(<FaqScreen />);

    expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument();
  });

  it('shows edit button for user with edit_faq permission', () => {
    const editorUser: User = {
      ...baseUser,
      roles: [{ id: 'role-1', name: 'faq-editor', isDefault: true, permissions: ['edit_faq'] }],
    };
    useAuthStore.setState({ status: 'authed', user: editorUser, accessToken: 'token' });
    mockUseFaq.mockReturnValue({
      isPending: false,
      isError: false,
      data: baseFaqData,
    } as ReturnType<typeof useFaq>);

    renderWith(<FaqScreen />);

    expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument();
  });
});
