import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';
import { makeUser as makeSharedUser } from '@/test/fixtures';

import { JoinRequestMessageEditors } from './JoinRequestMessageEditors';

vi.mock('@/api/client', () => ({
  setAuthBridge: vi.fn(),
  authClient: { post: vi.fn(), get: vi.fn() },
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/api/content', () => ({
  useWelcomeTemplate: () => ({
    data: { body: 'hi ${FIRST_NAME}', updatedAt: '2026-01-01' },
    isPending: false,
    isError: false,
  }),
  useUpdateWelcomeTemplate: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useTentativeApprovalMessage: () => ({
    data: { body: 'hi ${FIRST_NAME}, welcome', updatedAt: '2026-01-01' },
    isPending: false,
    isError: false,
  }),
  useUpdateTentativeApprovalMessage: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useMemberPromotionMessage: () => ({ data: undefined, isPending: false, isError: false }),
  useWhatsAppLink: () => ({
    data: { link: 'https://chat.whatsapp.com/abc123', updatedAt: '2026-01-01' },
    isPending: false,
    isError: false,
  }),
  useUpdateWhatsAppLink: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

function makeUser(overrides?: Partial<User>): User {
  return makeSharedUser({
    id: 'u1',
    phoneNumber: '+12125550000',
    firstName: 'Vetter',
    lastName: 'Vee',
    fullName: 'Vetter Vee',
    ...overrides,
  });
}

beforeEach(() => {
  useAuthStore.setState({ status: 'idle', user: null, accessToken: null });
});

function renderEditors(user: User | null) {
  useAuthStore.setState({
    status: user ? 'authed' : 'idle',
    user,
    accessToken: user ? 'tok' : null,
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <JoinRequestMessageEditors />
    </QueryClientProvider>,
  );
}

describe('JoinRequestMessageEditors', () => {
  it('renders nothing without permission', () => {
    const { container } = renderEditors(makeUser());
    expect(container).toBeEmptyDOMElement();
  });

  it('renders a template select with all options with permission', () => {
    const user = makeUser({
      roles: [
        { id: 'r1', name: 'vetter', isDefault: false, permissions: ['approve_join_requests'] },
      ],
    });
    renderEditors(user);
    const select = screen.getByLabelText('message templates');
    expect(select).toBeInTheDocument();
    expect(
      screen.getByRole('option', { name: /edit shared welcome template/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('option', { name: /edit tentative approval message/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('option', { name: /edit member promotion message/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /edit whatsapp link/i })).toBeInTheDocument();
  });

  it('opens the whatsapp link editor dialog when selected', async () => {
    const { default: userEvent } = await import('@testing-library/user-event');
    const user = makeUser({
      roles: [
        { id: 'r1', name: 'vetter', isDefault: false, permissions: ['approve_join_requests'] },
      ],
    });
    renderEditors(user);
    await userEvent.selectOptions(screen.getByLabelText('message templates'), 'edit whatsapp link');
    expect(screen.getByLabelText('whatsapp link')).toBeInTheDocument();
  });
});
