import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';

import SurveyPreviewScreen from './SurveyPreviewScreen';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), put: vi.fn() },
  authClient: { post: vi.fn() },
  setAuthBridge: vi.fn(),
}));

const mockedGet = vi.mocked(apiClient.get);

const wireSurvey = {
  id: 'srv-1',
  title: 'diet survey',
  slug: 'diet',
  visibility: 'public',
  is_active: false,
  feedback_event_type: 'official',
  questions: [
    {
      id: 'diet',
      label: 'diet',
      field_type: 'radio',
      options: ['vegan', 'veg'],
      required: false,
      display_order: 0,
    },
    {
      id: 'why',
      label: 'why vegan',
      field_type: 'text',
      required: true,
      display_order: 1,
      show_if: { question_id: 'diet', operator: 'equals', value: 'vegan' },
    },
  ],
};

function renderScreen() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/admin/surveys/srv-1/preview']}>
        <Routes>
          <Route path="/admin/surveys/:id/preview" element={<SurveyPreviewScreen />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockResolvedValue({ data: wireSurvey });
});

describe('SurveyPreviewScreen', () => {
  it('shows the questions of a closed feedback survey from the admin endpoint', async () => {
    renderScreen();

    expect(await screen.findByRole('status')).toHaveTextContent("preview — answers won't be saved");
    expect(screen.getByRole('heading', { name: 'diet survey' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'vegan' })).toBeInTheDocument();
    expect(mockedGet).toHaveBeenCalledWith('/api/community/surveys/srv-1/admin/');
  });

  it('has no way to submit', async () => {
    renderScreen();

    await screen.findByRole('radio', { name: 'vegan' });
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('reveals conditional questions as answers change', async () => {
    const user = userEvent.setup();
    renderScreen();

    await user.click(await screen.findByRole('radio', { name: 'vegan' }));
    expect(screen.getByRole('textbox', { name: /why vegan/ })).toBeInTheDocument();
  });

  it('links back to the builder', async () => {
    renderScreen();

    expect(await screen.findByRole('link', { name: '← back to editing' })).toHaveAttribute(
      'href',
      '/admin/surveys/srv-1',
    );
  });
});
