import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

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

import JoinScreen from './JoinScreen';
import JoinSuccessScreen from './JoinSuccessScreen';
import { useJoinQuestions, useSubmitJoinRequest } from '@/api/join';

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

function renderWith(component: React.ReactElement, initialRoute = '/join') {
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
  it('renders required form fields (display name, phone)', () => {
    renderWith(<JoinScreen />);

    expect(screen.getByLabelText(/display name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/phone number/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /submit request/i })).toBeInTheDocument();
  });

  it('shows validation error when required fields are empty on submit', async () => {
    const user = userEvent.setup();
    renderWith(<JoinScreen />);

    await user.click(screen.getByRole('button', { name: /submit request/i }));

    await waitFor(() => {
      expect(screen.getByText('name required')).toBeInTheDocument();
    });
    expect(screen.getByText('phone required')).toBeInTheDocument();
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

    await user.type(screen.getByLabelText(/display name/i), 'Jane Smith');
    await user.type(screen.getByLabelText(/phone number/i), '+15551234567');
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

    await user.type(screen.getByLabelText(/display name/i), 'Jane Smith');
    await user.type(screen.getByLabelText(/phone number/i), '+15551234567');
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
    await user.type(screen.getByLabelText(/display name/i), 'Alex Jones');
    await user.type(screen.getByLabelText(/phone number/i), '+15559876543');

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
