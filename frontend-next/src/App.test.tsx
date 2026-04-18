import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import LoginScreen from './screens/auth/LoginScreen';

const loginMock = vi.fn();

vi.mock('./api/auth', () => ({
  login: vi.fn(),
  magicLogin: vi.fn(),
  restoreSession: vi.fn(),
  logout: vi.fn(),
  fetchMe: vi.fn(),
  completeOnboarding: vi.fn(),
  changePassword: vi.fn(),
}));

vi.mock('./auth/store', () => ({
  useAuthStore: (selector: (s: { login: typeof loginMock }) => unknown) =>
    selector({ login: loginMock }),
}));

const checkPhoneMock = vi.fn<(phone: string) => Promise<'member' | 'pending' | 'unknown'>>();
vi.mock('./api/join', () => ({
  checkPhone: (phone: string) => checkPhoneMock(phone),
}));

const toastErrorMock = vi.fn<(message: string) => void>();
vi.mock('sonner', () => ({
  toast: {
    error: (message: string) => {
      toastErrorMock(message);
    },
  },
}));

function renderWith(initialEntries: string[] = ['/login']) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/login" element={<LoginScreen />} />
          <Route path="/join" element={<div>join page</div>} />
          <Route path="/calendar" element={<div>calendar page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// 212 is a real NYC area code — 555 numbers fail isValidPhoneNumber.
// PhoneInput accepts national-format input when the country dropdown is US.
const US_PHONE_NATIONAL = '2125551234';

describe('LoginScreen', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the phone step initially', () => {
    renderWith();
    expect(screen.getByLabelText(/phone number/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /continue/i })).toBeInTheDocument();
    expect(screen.queryByLabelText(/^password$/i)).not.toBeInTheDocument();
  });

  it('advances to password step when phone is recognized', async () => {
    checkPhoneMock.mockResolvedValueOnce('member');
    const user = userEvent.setup();
    renderWith();

    await user.type(screen.getByLabelText(/phone number/i), US_PHONE_NATIONAL);
    await user.click(screen.getByRole('button', { name: /continue/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('navigates to /join when phone is unknown', async () => {
    checkPhoneMock.mockResolvedValueOnce('unknown');
    const user = userEvent.setup();
    renderWith();

    await user.type(screen.getByLabelText(/phone number/i), US_PHONE_NATIONAL);
    await user.click(screen.getByRole('button', { name: /continue/i }));

    await waitFor(() => {
      expect(screen.getByText(/join page/i)).toBeInTheDocument();
    });
  });

  it('shows the pending step when phone has a pending join request', async () => {
    checkPhoneMock.mockResolvedValueOnce('pending');
    const user = userEvent.setup();
    renderWith();

    await user.type(screen.getByLabelText(/phone number/i), US_PHONE_NATIONAL);
    await user.click(screen.getByRole('button', { name: /continue/i }));

    await waitFor(() => {
      expect(screen.getByText(/under review/i)).toBeInTheDocument();
    });
  });

  it('shows toast + inline error on 401 and stays on password step', async () => {
    checkPhoneMock.mockResolvedValueOnce('member');
    loginMock.mockRejectedValueOnce(
      Object.assign(new Error('401'), {
        isAxiosError: true,
        response: { status: 401, data: { detail: 'invalid' } },
      }),
    );
    const user = userEvent.setup();
    renderWith();

    await user.type(screen.getByLabelText(/phone number/i), US_PHONE_NATIONAL);
    await user.click(screen.getByRole('button', { name: /continue/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(/^password$/i), 'wrongpassword');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith('invalid phone or password');
    });
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.getByText(/invalid phone or password/i)).toBeInTheDocument();
  });

  it('shows invited banner when ?invited=true', () => {
    renderWith(['/login?invited=true']);
    expect(screen.getByText(/you've been invited/i)).toBeInTheDocument();
  });
});
