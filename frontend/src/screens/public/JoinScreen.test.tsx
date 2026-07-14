import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/join', () => ({
  useJoinQuestions: vi.fn(),
  useSubmitJoinRequest: vi.fn(),
  AlreadyInvitedError: class AlreadyInvitedError extends Error {
    constructor() {
      super('already_invited');
      this.name = 'AlreadyInvitedError';
    }
  },
}));

import { useJoinQuestions, useSubmitJoinRequest } from '@/api/join';

import JoinScreen from './JoinScreen';
import JoinSuccessScreen from './JoinSuccessScreen';

const mockUseJoinQuestions = vi.mocked(useJoinQuestions);
const mockUseSubmitJoinRequest = vi.mocked(useSubmitJoinRequest);

const emptyQuestionsResult = {
  isPending: false,
  isError: false,
  data: [],
} as unknown as ReturnType<typeof useJoinQuestions>;

const defaultSubmitResult = {
  isPending: false,
  isError: false,
  mutateAsync: vi.fn(),
} as unknown as ReturnType<typeof useSubmitJoinRequest>;

// One-shot fill via fireEvent.change: key-by-key typing re-renders the country
// <select> on every keystroke, so a single change event is much cheaper.
function fillPhone(value = '(555) 123-4567') {
  fireEvent.change(screen.getByLabelText(/phone number/i), { target: { value } });
}

function renderWith(component: ReactElement, initialRoute = '/join') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialRoute]}>{component}</MemoryRouter>
    </QueryClientProvider>,
  );
}

function renderWithRoutes(initialRoute = '/join') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="/join" element={<JoinScreen />} />
          <Route path="/join/success" element={<JoinSuccessScreen />} />
          <Route path="/login" element={<div>login page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockUseJoinQuestions.mockReturnValue(emptyQuestionsResult);
  mockUseSubmitJoinRequest.mockReturnValue(defaultSubmitResult);
});

describe('JoinScreen', () => {
  it('renders required form fields (first name, last name, phone)', () => {
    renderWith(<JoinScreen />);

    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/last name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/phone number/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /submit request/i })).toBeInTheDocument();
  });

  it('shows validation error when required fields are empty on submit', async () => {
    const user = userEvent.setup();
    renderWith(<JoinScreen />);

    await user.click(screen.getByRole('button', { name: /submit request/i }));

    await waitFor(() => {
      expect(screen.getByText('first name required')).toBeInTheDocument();
    });
    expect(screen.getByText('last name required')).toBeInTheDocument();
    expect(screen.getByText('phone required')).toBeInTheDocument();
    expect(screen.getByText(/please agree to receive sms/i)).toBeInTheDocument();
  });

  it('blocks submit when name + phone are filled but sms consent is unchecked', async () => {
    const mutateAsync = vi.fn();
    mockUseSubmitJoinRequest.mockReturnValue({
      ...defaultSubmitResult,
      mutateAsync,
    } as unknown as ReturnType<typeof useSubmitJoinRequest>);

    const user = userEvent.setup();
    renderWith(<JoinScreen />);

    await user.type(screen.getByLabelText(/first name/i), 'Jane');
    await user.type(screen.getByLabelText(/last name/i), 'Smith');
    fillPhone();
    await user.type(screen.getByLabelText(/email/i), 'jane@example.com');
    await user.click(screen.getByRole('button', { name: /submit request/i }));

    await waitFor(() => {
      expect(screen.getByText(/please agree to receive sms/i)).toBeInTheDocument();
    });
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it('passes smsConsent + guidelinesConsent: true to the API when both boxes are checked', async () => {
    const mutateAsync = vi.fn().mockResolvedValueOnce(undefined);
    mockUseSubmitJoinRequest.mockReturnValue({
      ...defaultSubmitResult,
      mutateAsync,
    } as unknown as ReturnType<typeof useSubmitJoinRequest>);

    const user = userEvent.setup();
    renderWithRoutes();

    await user.type(screen.getByLabelText(/first name/i), 'Jane');
    await user.type(screen.getByLabelText(/last name/i), 'Smith');
    fillPhone();
    await user.type(screen.getByLabelText(/email/i), 'jane@example.com');
    await user.click(screen.getByRole('checkbox', { name: /sms policy/i }));
    await user.click(screen.getByRole('checkbox', { name: /community guidelines/i }));
    await user.click(screen.getByRole('button', { name: /submit request/i }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalled();
    });
    const arg = mutateAsync.mock.calls[0]?.[0] as {
      smsConsent: boolean;
      guidelinesConsent: boolean;
    };
    expect(arg.smsConsent).toBe(true);
    expect(arg.guidelinesConsent).toBe(true);
  });

  it('blocks submit when sms consent is checked but guidelines consent is not', async () => {
    const mutateAsync = vi.fn();
    mockUseSubmitJoinRequest.mockReturnValue({
      ...defaultSubmitResult,
      mutateAsync,
    } as unknown as ReturnType<typeof useSubmitJoinRequest>);

    const user = userEvent.setup();
    renderWith(<JoinScreen />);

    await user.type(screen.getByLabelText(/first name/i), 'Jane');
    await user.type(screen.getByLabelText(/last name/i), 'Smith');
    fillPhone();
    await user.type(screen.getByLabelText(/email/i), 'jane@example.com');
    await user.click(screen.getByRole('checkbox', { name: /sms policy/i }));
    await user.click(screen.getByRole('button', { name: /submit request/i }));

    await waitFor(() => {
      expect(
        screen.getByText(
          /please read and confirm you agree to the guidelines and community agreements/i,
        ),
      ).toBeInTheDocument();
    });
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it('shows error message on API submission failure', async () => {
    const mutateAsync = vi.fn().mockRejectedValueOnce(
      Object.assign(new Error('server error'), {
        isAxiosError: true,
        response: { status: 400, data: { detail: 'something went wrong on the server' } },
      }),
    );
    mockUseSubmitJoinRequest.mockReturnValue({
      ...defaultSubmitResult,
      mutateAsync,
    } as unknown as ReturnType<typeof useSubmitJoinRequest>);

    const user = userEvent.setup();
    renderWith(<JoinScreen />);

    await user.type(screen.getByLabelText(/first name/i), 'Jane');
    await user.type(screen.getByLabelText(/last name/i), 'Smith');
    fillPhone();
    await user.type(screen.getByLabelText(/email/i), 'jane@example.com');
    await user.click(screen.getByRole('checkbox', { name: /sms policy/i }));
    await user.click(screen.getByRole('checkbox', { name: /community guidelines/i }));
    await user.click(screen.getByRole('button', { name: /submit request/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('something went wrong on the server');
    });
  });

  it('navigates to /join/success on successful submission', async () => {
    const mutateAsync = vi.fn().mockResolvedValueOnce(undefined);
    mockUseSubmitJoinRequest.mockReturnValue({
      ...defaultSubmitResult,
      mutateAsync,
    } as unknown as ReturnType<typeof useSubmitJoinRequest>);

    const user = userEvent.setup();
    renderWithRoutes();

    await user.type(screen.getByLabelText(/first name/i), 'Jane');
    await user.type(screen.getByLabelText(/last name/i), 'Smith');
    fillPhone();
    await user.type(screen.getByLabelText(/email/i), 'jane@example.com');
    await user.click(screen.getByRole('checkbox', { name: /sms policy/i }));
    await user.click(screen.getByRole('checkbox', { name: /community guidelines/i }));
    await user.click(screen.getByRole('button', { name: /submit request/i }));

    await waitFor(() => {
      expect(screen.getByText(/request received/i)).toBeInTheDocument();
    });
  });

  it('end-to-end: complete the form and submit → renders success screen', async () => {
    const mutateAsync = vi.fn().mockResolvedValueOnce(undefined);
    mockUseSubmitJoinRequest.mockReturnValue({
      ...defaultSubmitResult,
      mutateAsync,
    } as unknown as ReturnType<typeof useSubmitJoinRequest>);

    const user = userEvent.setup();
    renderWithRoutes();

    // Fill out form
    await user.type(screen.getByLabelText(/first name/i), 'Alex');
    await user.type(screen.getByLabelText(/last name/i), 'Jones');
    fillPhone();
    await user.type(screen.getByLabelText(/email/i), 'alex@example.com');
    await user.click(screen.getByRole('checkbox', { name: /sms policy/i }));
    await user.click(screen.getByRole('checkbox', { name: /community guidelines/i }));

    // Submit
    await user.click(screen.getByRole('button', { name: /submit request/i }));

    // Success screen rendered
    await waitFor(() => {
      expect(screen.getByText(/request received/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/vetting member will review/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /back to home/i })).toBeInTheDocument();
  });
});

describe('email validation', () => {
  it('shows email required when blank', async () => {
    renderWith(<JoinScreen />);
    await userEvent.type(screen.getByLabelText(/first name/i), 'Tester');
    await userEvent.type(screen.getByLabelText(/last name/i), 'Tester');
    fillPhone();
    await userEvent.click(screen.getByLabelText(/i agree to pda's/i));
    await userEvent.click(screen.getByRole('button', { name: /submit request/i }));
    expect(await screen.findByText(/email required/i)).toBeInTheDocument();
  });

  it('passes email to submit', async () => {
    const submit = vi.fn().mockResolvedValue(undefined);
    mockUseSubmitJoinRequest.mockReturnValue({
      mutateAsync: submit,
      isPending: false,
    } as unknown as ReturnType<typeof useSubmitJoinRequest>);

    renderWith(<JoinScreen />);
    await userEvent.type(screen.getByLabelText(/first name/i), 'Tester');
    await userEvent.type(screen.getByLabelText(/last name/i), 'Tester');
    fillPhone();
    await userEvent.type(screen.getByLabelText(/email/i), 'Tester@Example.com');
    await userEvent.click(screen.getByLabelText(/i agree to pda's/i));
    await userEvent.click(screen.getByLabelText(/i have read and agree to the/i));
    await userEvent.click(screen.getByRole('button', { name: /submit request/i }));
    expect(submit).toHaveBeenCalledWith(
      expect.objectContaining({
        firstName: 'Tester',
        lastName: 'Tester',
        email: 'Tester@Example.com',
      }),
    );
  });
});
