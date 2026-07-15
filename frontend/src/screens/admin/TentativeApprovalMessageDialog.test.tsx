import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';
import { makeUser as makeSharedUser } from '@/test/fixtures';

import { TentativeApprovalMessageDialog } from './TentativeApprovalMessageDialog';

vi.mock('@/api/client', () => ({
  setAuthBridge: vi.fn(),
  authClient: { post: vi.fn(), get: vi.fn() },
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/api/content', () => ({
  useTentativeApprovalMessage: () => ({
    data: {
      body: 'hi ${FIRST_NAME}, from ${SENDER_NAME} — you are tentatively in',
      updatedAt: '2026-01-01',
    },
    isPending: false,
    isError: false,
  }),
  useUpdateTentativeApprovalMessage: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useWhatsAppLink: () => ({
    data: { link: '', updatedAt: '2026-01-01' },
    isPending: false,
    isError: false,
  }),
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

function renderDialog(user: User | null) {
  useAuthStore.setState({
    status: user ? 'authed' : 'idle',
    user,
    accessToken: user ? 'tok' : null,
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <TentativeApprovalMessageDialog
        open
        onClose={() => {}}
        fullName="Sam Vetterson"
        firstName="Sam"
        phoneNumber="+12025551234"
      />
    </QueryClientProvider>,
  );
}

describe('TentativeApprovalMessageDialog', () => {
  it('renders sms and whatsapp buttons with substituted hrefs, no magic link', () => {
    renderDialog(makeUser());
    const sms = screen.getByText('send via sms').closest('a');
    const wa = screen.getByText('send via whatsapp').closest('a');
    expect(sms?.getAttribute('href')).toContain('sms:+12025551234?body=');
    expect(sms?.getAttribute('href')).toContain(
      encodeURIComponent('hi Sam, from Vetter — you are tentatively in'),
    );
    expect(wa?.getAttribute('href')).toContain('https://wa.me/12025551234?text=');
    expect(screen.queryByText(/magic-login/i)).toBeNull();
    expect(screen.queryByRole('button', { name: /copy link/i })).toBeNull();
  });

  it('hides edit-template trigger without permission', () => {
    renderDialog(makeUser());
    expect(screen.queryByRole('button', { name: /edit tentative approval message/i })).toBeNull();
  });

  it('shows edit-template trigger with permission', () => {
    const user = makeUser({
      roles: [
        {
          id: 'r1',
          name: 'vetter',
          isDefault: false,
          permissions: ['approve_join_requests'],
        },
      ],
    });
    renderDialog(user);
    expect(
      screen.getByRole('button', { name: /edit tentative approval message/i }),
    ).toBeInTheDocument();
  });
});
