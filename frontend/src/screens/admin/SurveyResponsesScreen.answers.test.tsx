import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { format } from 'date-fns';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';

import SurveyResponsesScreen from './SurveyResponsesScreen';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), put: vi.fn() },
  authClient: { post: vi.fn() },
  setAuthBridge: vi.fn(),
}));

const mockedGet = vi.mocked(apiClient.get);

function renderScreen(surveyId = 'srv-1') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/admin/surveys/${surveyId}/responses`]}>
        <Routes>
          <Route path="/admin/surveys/:id/responses" element={<SurveyResponsesScreen />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const wireSurvey = {
  id: 'srv-1',
  title: 'checkin',
  slug: 'checkin',
  visibility: 'public',
  is_active: true,
  questions: [
    { id: 'qt', label: 'mood', field_type: 'text', required: false, display_order: 0 },
    {
      id: 'qc',
      label: 'flavors',
      field_type: 'checkbox',
      options: ['vanilla', 'choc'],
      required: false,
      display_order: 1,
    },
    {
      id: 'qd',
      label: 'availability',
      field_type: 'datetime_poll',
      options: ['2030-01-01T18:00:00+00:00'],
      required: false,
      display_order: 2,
    },
    { id: 'qs', label: 'about you', field_type: 'section', display_order: 3 },
  ],
  my_response_id: null,
  my_answers: null,
  poll_result: null,
};

const wireResponse = {
  id: 'r1',
  user_id: 'u1',
  user_name: 'ada',
  submitted_at: '2026-01-01T12:00:00Z',
  answers: {
    qt: { label: 'mood', answer: 'great' },
    qc: { label: 'flavors', answer: 'vanilla,choc' },
    qd: { label: 'availability', answer: { '2030-01-01T18:00:00+00:00': 'yes' } },
  },
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedGet.mockImplementation((url: string) => {
    if (url.includes('/tallies/')) return Promise.resolve({ data: [] });
    if (url.includes('/summary/')) return Promise.resolve({ data: [] });
    if (url.includes('/responses/')) return Promise.resolve({ data: [wireResponse] });
    return Promise.resolve({ data: wireSurvey });
  });
});

describe('SurveyResponsesScreen', () => {
  it('renders a response row with text, checkbox, and datetime poll answers', async () => {
    renderScreen();

    await screen.findByText('ada');
    expect(screen.getByText('great')).toBeInTheDocument();
    expect(screen.getByText('vanilla,choc')).toBeInTheDocument();
    expect(
      screen.getByRole('cell', {
        name: `${format(new Date('2030-01-01T18:00:00+00:00'), 'MMM d, yyyy h:mm a').toLowerCase()}: yes`,
      }),
    ).toBeInTheDocument();

    expect(screen.getByRole('columnheader', { name: 'mood' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'flavors' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'availability' })).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'about you' })).not.toBeInTheDocument();
  });

  it('lists entries in the individual view and opens one on click', async () => {
    const user = userEvent.setup();
    renderScreen();

    await user.click(await screen.findByRole('radio', { name: 'individual' }));
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.queryByText('great')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /^ada/ }));
    const dialog = screen.getByRole('dialog', { name: 'ada' });
    expect(within(dialog).getByText('great')).toBeInTheDocument();
    expect(within(dialog).getByRole('heading', { name: 'about you' })).toBeInTheDocument();
  });

  it('labels anonymous submitters', async () => {
    mockedGet.mockImplementation((url: string) => {
      if (url.includes('/responses/'))
        return Promise.resolve({ data: [{ ...wireResponse, user_name: null }] });
      if (url.includes('/summary/') || url.includes('/tallies/'))
        return Promise.resolve({ data: [] });
      return Promise.resolve({ data: { ...wireSurvey, anonymous: true } });
    });
    renderScreen();

    expect(await screen.findByText('anonymous')).toBeInTheDocument();
  });
});
