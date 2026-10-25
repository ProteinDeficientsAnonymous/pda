import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';

import { SurveyThankYouCard } from './SurveyThankYouCard';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), put: vi.fn() },
  authClient: { post: vi.fn() },
  setAuthBridge: vi.fn(),
}));

const mockedPatch = vi.mocked(apiClient.patch);

function renderCard(confirmationMessage = '') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <SurveyThankYouCard surveyId="srv-1" confirmationMessage={confirmationMessage} />
    </QueryClientProvider>,
  );
}

const wireSurvey = { id: 'srv-1', title: 't', slug: 's', visibility: 'public', is_active: true };

beforeEach(() => {
  vi.clearAllMocks();
});

describe('SurveyThankYouCard', () => {
  it('shows the default message as a placeholder when blank', () => {
    renderCard();
    const field = screen.getByLabelText('thank-you message');
    expect(field).toHaveValue('');
    expect(field).toHaveAttribute('placeholder', 'thanks for filling out our survey!');
    expect(screen.getByText('always last')).toBeInTheDocument();
  });

  it('saves a trimmed message on blur', async () => {
    mockedPatch.mockResolvedValueOnce({ data: { ...wireSurvey, confirmation_message: 'yay' } });
    renderCard();
    const field = screen.getByLabelText('thank-you message');
    fireEvent.change(field, { target: { value: '  yay  ' } });
    fireEvent.blur(field);

    await waitFor(() => {
      expect(mockedPatch).toHaveBeenCalledWith('/api/community/surveys/srv-1/', {
        confirmation_message: 'yay',
      });
    });
    expect(await screen.findByText('saved')).toBeInTheDocument();
  });

  it('clearing the message saves blank so the default is used', async () => {
    mockedPatch.mockResolvedValueOnce({ data: { ...wireSurvey, confirmation_message: '' } });
    renderCard('custom');
    const field = screen.getByLabelText('thank-you message');
    fireEvent.change(field, { target: { value: '' } });
    fireEvent.blur(field);

    await waitFor(() => {
      expect(mockedPatch).toHaveBeenCalledWith('/api/community/surveys/srv-1/', {
        confirmation_message: '',
      });
    });
  });

  it('skips the save when nothing changed', () => {
    renderCard('custom');
    fireEvent.blur(screen.getByLabelText('thank-you message'));
    expect(mockedPatch).not.toHaveBeenCalled();
  });

  it('shows an error when the save fails', async () => {
    mockedPatch.mockRejectedValueOnce(new Error('boom'));
    renderCard();
    const field = screen.getByLabelText('thank-you message');
    fireEvent.change(field, { target: { value: 'hi' } });
    fireEvent.blur(field);
    expect(await screen.findByRole('alert')).toHaveTextContent(
      "couldn't save the message — try again",
    );
  });
});
