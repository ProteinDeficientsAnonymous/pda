import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';
import { ApprovalCredentialsDialog } from './ApprovalCredentialsDialog';

vi.mock('@/api/client', () => ({
  setAuthBridge: vi.fn(),
  authClient: { post: vi.fn(), get: vi.fn() },
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/api/content', () => ({
  useWelcomeTemplate: () => ({
    data: { body: 'hi ${NAME}, from ${SENDER_NAME}: ${MAGIC_LINK}', updatedAt: '2026-01-01' },
    isPending: false,
    isError: false,
  }),
  useUpdateWelcomeTemplate: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

function makeUser(overrides?: Partial<User>): User {
  return {
    id: 'u1',
    phoneNumber: '+12125550000',
    displayName: 'Vetter Vee',
    email: '',
    bio: '',
    isSuperuser: false,
    isStaff: false,
    needsOnboarding: false,
    showPhone: false,
    showEmail: false,
    weekStart: 'sunday',
    calendarFeedScope: 'all',
    profilePhotoUrl: '',
    photoUpdatedAt: null,
    roles: [],
    ...overrides,
  };
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
      <ApprovalCredentialsDialog
        open
        onClose={() => {}}
        displayName="Sam"
        phoneNumber="+12025551234"
        magicLinkToken="abc123"
      />
    </QueryClientProvider>,
  );
}

describe('ApprovalCredentialsDialog', () => {
  it('renders sms and whatsapp buttons with substituted hrefs', () => {
    renderDialog(makeUser());
    const sms = screen.getByText('send via sms').closest('a');
    const wa = screen.getByText('send via whatsapp').closest('a');
    // Expected body: "hi Sam, from Vetter Vee: <magic-link>"
    expect(sms?.getAttribute('href')).toContain('sms:+12025551234?body=');
    expect(sms?.getAttribute('href')).toContain(encodeURIComponent('hi Sam, from Vetter Vee: '));
    expect(wa?.getAttribute('href')).toContain('https://wa.me/12025551234?text=');
    expect(wa?.getAttribute('href')).toContain(encodeURIComponent('hi Sam, from Vetter Vee: '));
  });

  it('hides edit-template trigger without permission', () => {
    renderDialog(makeUser());
    expect(screen.queryByRole('button', { name: /edit shared welcome template/i })).toBeNull();
  });

  it('shows edit-template trigger with permission', () => {
    const user = makeUser({
      roles: [
        {
          id: 'r1',
          name: 'vetter',
          isDefault: false,
          permissions: ['edit_welcome_message'],
        },
      ],
    });
    renderDialog(user);
    expect(
      screen.getByRole('button', { name: /edit shared welcome template/i }),
    ).toBeInTheDocument();
  });
});
