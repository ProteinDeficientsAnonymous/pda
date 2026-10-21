import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';
import { makeUser as makeSharedUser } from '@/test/fixtures';

import { MemberPromotionMessageDialog } from './MemberPromotionMessageDialog';

vi.mock('@/api/client', () => ({
  setAuthBridge: vi.fn(),
  authClient: { post: vi.fn(), get: vi.fn() },
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

const { templateState } = vi.hoisted(() => ({
  templateState: {
    data: { body: 'hi ${FIRST_NAME}, from ${SENDER_NAME}: ${MAGIC_LINK}', updatedAt: '2026-01-01' },
  } as { data: { body: string; updatedAt: string } | undefined },
}));

vi.mock('@/api/content', () => ({
  useMemberPromotionMessage: () => ({
    data: templateState.data,
    isPending: false,
    isError: false,
  }),
  useUpdateMemberPromotionMessage: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useWhatsAppLink: () => ({
    data: { link: '', updatedAt: '2026-01-01' },
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
  templateState.data = {
    body: 'hi ${FIRST_NAME}, from ${SENDER_NAME}: ${MAGIC_LINK}',
    updatedAt: '2026-01-01',
  };
});

function renderDialog(user: User | null, firstName = 'Sam', phoneNumber = '+12025551234') {
  useAuthStore.setState({
    status: user ? 'authed' : 'idle',
    user,
    accessToken: user ? 'tok' : null,
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemberPromotionMessageDialog
        open
        onClose={() => {}}
        fullName="Sam Vetterson"
        firstName={firstName}
        phoneNumber={phoneNumber}
      />
    </QueryClientProvider>,
  );
}

describe('MemberPromotionMessageDialog', () => {
  it('offers no login link — a promoted member already has one', () => {
    renderDialog(makeUser());
    expect(screen.queryByText(/magic-login/)).toBeNull();
    expect(screen.queryByRole('button', { name: /copy link/i })).toBeNull();
  });

  it('swallows a retired MAGIC_LINK placeholder left in the template', () => {
    renderDialog(makeUser());
    const sms = screen.getByText('send via sms').closest('a');
    expect(sms?.getAttribute('href')).not.toContain('MAGIC_LINK');
    expect(sms?.getAttribute('href')).not.toContain('magic-login');
  });

  it('renders sms and whatsapp buttons with substituted hrefs', () => {
    renderDialog(makeUser());
    const sms = screen.getByText('send via sms').closest('a');
    const wa = screen.getByText('send via whatsapp').closest('a');
    expect(sms?.getAttribute('href')).toContain('sms:+12025551234?body=');
    expect(sms?.getAttribute('href')).toContain(encodeURIComponent('hi Sam, from Vetter: '));
    expect(wa?.getAttribute('href')).toContain('https://wa.me/12025551234?text=');
  });

  it('falls back to a plain body when the template is unavailable', () => {
    templateState.data = undefined;
    renderDialog(makeUser());
    expect(screen.getByText(/you're a full member now/)).toBeInTheDocument();
  });

  it('renders the fallback without a first name', () => {
    templateState.data = undefined;
    // null, not undefined — a default parameter would swallow undefined.
    renderDialog(makeUser(), null as unknown as string);
    expect(screen.getByText(/you're a full member now/)).toBeInTheDocument();
    expect(screen.queryByText(/undefined/)).toBeNull();
  });

  it('renders without a phone number on the row', () => {
    renderDialog(makeUser(), 'Sam', null as unknown as string);
    expect(screen.getByText('send via sms')).toBeInTheDocument();
    expect(screen.getByText('send via whatsapp')).toBeInTheDocument();
  });

  it('hides edit-template trigger without permission', () => {
    renderDialog(makeUser());
    expect(screen.queryByRole('button', { name: /edit member promotion message/i })).toBeNull();
  });

  it('shows the edit trigger with permission', () => {
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
      screen.getByRole('button', { name: /edit member promotion message/i }),
    ).toBeInTheDocument();
  });
});
