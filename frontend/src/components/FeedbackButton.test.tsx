import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';

const submitFeedbackMock = vi.fn();

vi.mock('@/api/feedback', () => ({
  useSubmitFeedback: vi.fn(),
}));

const toastSuccessMock = vi.fn();
const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    success: (msg: string, opts?: unknown) => {
      toastSuccessMock(msg, opts);
    },
    error: (msg: string) => {
      toastErrorMock(msg);
    },
  },
}));

import { useSubmitFeedback } from '@/api/feedback';
import { FeedbackButton } from './FeedbackButton';

const mockedUseSubmitFeedback = vi.mocked(useSubmitFeedback);

function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 'user-1',
    phoneNumber: '+12125551234',
    displayName: 'alice',
    email: 'alice@example.com',
    bio: '',
    isSuperuser: false,
    isStaff: false,
    needsOnboarding: false,
    showPhone: false,
    showEmail: false,
    weekStart: 'sunday',
    profilePhotoUrl: '',
    photoUpdatedAt: null,
    roles: [],
    ...overrides,
  };
}

function renderButton(initialPath = '/calendar') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <FeedbackButton />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ status: 'authed', user: makeUser(), accessToken: 'tok' });
  submitFeedbackMock.mockResolvedValue({ html_url: 'https://example.com/1' });
  mockedUseSubmitFeedback.mockReturnValue({
    mutateAsync: submitFeedbackMock,
    isPending: false,
  } as unknown as ReturnType<typeof useSubmitFeedback>);
});

describe('FeedbackButton', () => {
  it('renders the floating ? button with an accessible label for authed users', () => {
    renderButton();
    const btn = screen.getByRole('button', { name: /send feedback/i });
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveTextContent('?');
  });

  it('is hidden when the user is not authenticated', () => {
    useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
    renderButton();
    expect(screen.queryByRole('button', { name: /send feedback/i })).not.toBeInTheDocument();
  });

  it('opens the form dialog when the button is tapped', async () => {
    const user = userEvent.setup();
    renderButton();

    await user.click(screen.getByRole('button', { name: /send feedback/i }));

    expect(screen.getByRole('dialog', { name: /send feedback/i })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /^title$/i })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /^description$/i })).toBeInTheDocument();
  });

  it('enforces maxLength on the title and description fields', async () => {
    const user = userEvent.setup();
    renderButton();
    await user.click(screen.getByRole('button', { name: /send feedback/i }));

    expect(screen.getByRole('textbox', { name: /^title$/i })).toHaveAttribute('maxLength', '150');
    expect(screen.getByRole('textbox', { name: /^description$/i })).toHaveAttribute(
      'maxLength',
      '2000',
    );
  });

  it('cancel closes the dialog without submitting', async () => {
    const user = userEvent.setup();
    renderButton();
    await user.click(screen.getByRole('button', { name: /send feedback/i }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /cancel/i }));

    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: /send feedback/i })).not.toBeInTheDocument();
    });
    expect(submitFeedbackMock).not.toHaveBeenCalled();
  });

  it('shows required errors and does not submit when title or description are blank', async () => {
    const user = userEvent.setup();
    renderButton();
    await user.click(screen.getByRole('button', { name: /send feedback/i }));

    await user.click(screen.getByRole('button', { name: /^submit$/i }));

    expect(submitFeedbackMock).not.toHaveBeenCalled();
    // Two "required" labels, one per invalid field
    expect(screen.getAllByText(/required/i).length).toBeGreaterThanOrEqual(2);
  });

  it('submits the feedback with route, user-agent, and selected types, then toasts success', async () => {
    const user = userEvent.setup();
    Object.defineProperty(window.navigator, 'userAgent', {
      value: 'jsdom-test-agent',
      configurable: true,
    });
    renderButton('/events/mine');
    await user.click(screen.getByRole('button', { name: /send feedback/i }));

    await user.type(screen.getByRole('textbox', { name: /^title$/i }), 'crash on events');
    await user.type(screen.getByRole('textbox', { name: /^description$/i }), 'it explodes');
    await user.click(screen.getByRole('checkbox', { name: /^bug$/i }));
    await user.click(screen.getByRole('button', { name: /^submit$/i }));

    await waitFor(() => {
      expect(submitFeedbackMock).toHaveBeenCalledTimes(1);
    });
    const payload = submitFeedbackMock.mock.calls[0]?.[0];
    expect(payload).toMatchObject({
      title: 'crash on events',
      description: 'it explodes',
      feedbackTypes: ['bug'],
      metadata: {
        route: '/events/mine',
        userAgent: 'jsdom-test-agent',
        userDisplayName: 'alice',
        userPhone: '+12125551234',
      },
    });
    await waitFor(() => {
      expect(toastSuccessMock).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: /send feedback/i })).not.toBeInTheDocument();
    });
  });

  it('exposes the github issue url in the success toast action', async () => {
    submitFeedbackMock.mockResolvedValueOnce({
      html_url: 'https://github.com/owner/repo/issues/123',
    });
    const user = userEvent.setup();
    renderButton();
    await user.click(screen.getByRole('button', { name: /send feedback/i }));

    await user.type(screen.getByRole('textbox', { name: /^title$/i }), 't');
    await user.type(screen.getByRole('textbox', { name: /^description$/i }), 'd');
    await user.click(screen.getByRole('button', { name: /^submit$/i }));

    await waitFor(() => {
      expect(toastSuccessMock).toHaveBeenCalled();
    });
    const opts = toastSuccessMock.mock.calls[0]?.[1] as
      | { action?: { label?: string; onClick?: () => void } }
      | undefined;
    expect(opts?.action?.label).toBe('view your issue');
    expect(typeof opts?.action?.onClick).toBe('function');
  });

  it('shows an error toast and keeps the dialog open when submission fails', async () => {
    submitFeedbackMock.mockRejectedValueOnce(new Error('boom'));
    const user = userEvent.setup();
    renderButton();
    await user.click(screen.getByRole('button', { name: /send feedback/i }));

    await user.type(screen.getByRole('textbox', { name: /^title$/i }), 't');
    await user.type(screen.getByRole('textbox', { name: /^description$/i }), 'd');
    await user.click(screen.getByRole('button', { name: /^submit$/i }));

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalled();
    });
    // Dialog stays open so the user can retry
    expect(screen.getByRole('dialog', { name: /send feedback/i })).toBeInTheDocument();
    expect(toastSuccessMock).not.toHaveBeenCalled();
  });

  it('does not display route, user-agent, or other metadata in the open form', async () => {
    const user = userEvent.setup();
    Object.defineProperty(window.navigator, 'userAgent', {
      value: 'jsdom-metadata-probe',
      configurable: true,
    });
    renderButton('/events/mine');
    await user.click(screen.getByRole('button', { name: /send feedback/i }));

    const dialog = screen.getByRole('dialog', { name: /send feedback/i });
    // Metadata is collected silently — it should never be rendered in the UI.
    expect(dialog).not.toHaveTextContent('/events/mine');
    expect(dialog).not.toHaveTextContent('jsdom-metadata-probe');
    expect(dialog).not.toHaveTextContent('+12125551234');
    expect(dialog).not.toHaveTextContent(/user[\s-]?agent/i);
    expect(dialog).not.toHaveTextContent(/route/i);
  });
});
