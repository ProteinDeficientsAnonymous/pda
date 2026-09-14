import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import type { ReactNode } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import type { SurveyQuestion } from '@/api/surveyAdmin';

import SurveyBuilderScreen from './SurveyBuilderScreen';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), put: vi.fn() },
  authClient: { post: vi.fn() },
  setAuthBridge: vi.fn(),
}));

vi.mock('@/components/SortableList', () => ({
  SortableList: ({
    items,
    onReorder,
    renderItem,
  }: {
    items: SurveyQuestion[];
    onReorder: (ids: string[]) => void;
    renderItem: (item: SurveyQuestion) => ReactNode;
  }) => (
    <div>
      {items.map((item) => (
        <div key={item.id}>{renderItem(item)}</div>
      ))}
      <button
        type="button"
        onClick={() => {
          onReorder([items[1]!.id, items[0]!.id]);
        }}
      >
        simulate reorder
      </button>
    </div>
  ),
}));

const mockedGet = vi.mocked(apiClient.get);
const mockedPut = vi.mocked(apiClient.put);
const mockedDelete = vi.mocked(apiClient.delete);

function renderScreen(surveyId = 'srv-1') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/admin/surveys/${surveyId}`]}>
        <Routes>
          <Route path="/admin/surveys/:id" element={<SurveyBuilderScreen />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const wireSurvey = {
  id: 'srv-1',
  title: 'feedback survey',
  slug: 'feedback',
  visibility: 'public',
  is_active: true,
  questions: [
    { id: 'q1', label: 'first', field_type: 'text', required: false, display_order: 0 },
    { id: 'q2', label: 'second', field_type: 'text', required: false, display_order: 1 },
  ],
  my_response_id: null,
  my_answers: null,
  poll_result: null,
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('SurveyBuilderScreen', () => {
  it('reorders questions via the sortable list and calls the reorder endpoint', async () => {
    mockedGet.mockResolvedValueOnce({ data: wireSurvey });
    renderScreen();
    await screen.findByText('first');

    fireEvent.click(screen.getByRole('button', { name: 'simulate reorder' }));

    await waitFor(() => {
      expect(mockedPut).toHaveBeenCalledWith('/api/community/surveys/srv-1/questions/order/', {
        question_ids: ['q2', 'q1'],
      });
    });
  });

  it('asks for confirmation before deleting a question, then deletes on confirm', async () => {
    mockedGet.mockResolvedValueOnce({ data: wireSurvey });
    renderScreen();
    await screen.findByText('first');

    const [firstDeleteButton] = screen.getAllByRole('button', { name: 'delete' });
    fireEvent.click(firstDeleteButton!);

    const dialog = await screen.findByRole('dialog', { name: 'delete question' });
    expect(mockedDelete).not.toHaveBeenCalled();

    fireEvent.click(within(dialog).getByRole('button', { name: 'delete' }));

    await waitFor(() => {
      expect(mockedDelete).toHaveBeenCalledWith('/api/community/surveys/srv-1/questions/q1/');
    });
  });

  it('does not delete when the confirmation is cancelled', async () => {
    mockedGet.mockResolvedValueOnce({ data: wireSurvey });
    renderScreen();
    await screen.findByText('first');

    const [firstDeleteButton] = screen.getAllByRole('button', { name: 'delete' });
    fireEvent.click(firstDeleteButton!);

    const dialog = await screen.findByRole('dialog', { name: 'delete question' });
    fireEvent.click(within(dialog).getByRole('button', { name: 'cancel' }));

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
    expect(mockedDelete).not.toHaveBeenCalled();
  });
});
