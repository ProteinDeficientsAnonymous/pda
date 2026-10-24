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
const mockedPost = vi.mocked(apiClient.post);
const mockedPatch = vi.mocked(apiClient.patch);

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
    await screen.findByDisplayValue('first');

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
    await screen.findByDisplayValue('first');

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
    await screen.findByDisplayValue('first');

    const [firstDeleteButton] = screen.getAllByRole('button', { name: 'delete' });
    fireEvent.click(firstDeleteButton!);

    const dialog = await screen.findByRole('dialog', { name: 'delete question' });
    fireEvent.click(within(dialog).getByRole('button', { name: 'cancel' }));

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
    expect(mockedDelete).not.toHaveBeenCalled();
  });

  it('asks for confirmation before closing the survey, then closes on confirm', async () => {
    mockedGet.mockResolvedValue({ data: wireSurvey });
    mockedPatch.mockResolvedValueOnce({ data: { ...wireSurvey, is_active: false } });
    renderScreen();
    await screen.findByDisplayValue('first');

    fireEvent.click(screen.getByRole('button', { name: 'close survey' }));

    const dialog = await screen.findByRole('dialog', { name: 'close survey' });
    expect(mockedPatch).not.toHaveBeenCalled();

    fireEvent.click(within(dialog).getByRole('button', { name: 'close survey' }));

    await waitFor(() => {
      expect(mockedPatch).toHaveBeenCalledWith(
        '/api/community/surveys/srv-1/',
        expect.objectContaining({ is_active: false }),
      );
    });
  });

  it('does not close the survey when the confirmation is cancelled', async () => {
    mockedGet.mockResolvedValueOnce({ data: wireSurvey });
    renderScreen();
    await screen.findByDisplayValue('first');

    fireEvent.click(screen.getByRole('button', { name: 'close survey' }));

    const dialog = await screen.findByRole('dialog', { name: 'close survey' });
    fireEvent.click(within(dialog).getByRole('button', { name: 'cancel' }));

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
    expect(mockedPatch).not.toHaveBeenCalled();
  });

  it('reopens a closed survey without asking', async () => {
    mockedGet.mockResolvedValue({ data: { ...wireSurvey, is_active: false } });
    mockedPatch.mockResolvedValueOnce({ data: wireSurvey });
    renderScreen();
    await screen.findByDisplayValue('first');
    expect(screen.getByText(/· closed/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'reopen survey' }));

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await waitFor(() => {
      expect(mockedPatch).toHaveBeenCalledWith(
        '/api/community/surveys/srv-1/',
        expect.objectContaining({ is_active: true }),
      );
    });
  });

  it('adds a blank question inline without opening a dialog', async () => {
    mockedGet.mockResolvedValue({ data: wireSurvey });
    mockedPost.mockResolvedValueOnce({ data: { id: 'q3' } });
    renderScreen();
    await screen.findByDisplayValue('first');

    fireEvent.click(screen.getByRole('button', { name: '+ add question' }));

    await waitFor(() => {
      expect(mockedPost).toHaveBeenCalledWith('/api/community/surveys/srv-1/questions/', {
        label: 'untitled question',
        field_type: 'text',
        options: [],
        required: false,
        show_if: null,
      });
    });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('saves an edited label when the field loses focus', async () => {
    mockedGet.mockResolvedValue({ data: wireSurvey });
    mockedPatch.mockResolvedValueOnce({ data: {} });
    renderScreen();
    const input = await screen.findByDisplayValue('first');

    fireEvent.change(input, { target: { value: 'first, renamed' } });
    expect(mockedPatch).not.toHaveBeenCalled();
    fireEvent.blur(input);

    await waitFor(() => {
      expect(mockedPatch).toHaveBeenCalledWith('/api/community/surveys/srv-1/questions/q1/', {
        label: 'first, renamed',
        field_type: 'text',
        options: [],
        required: false,
        show_if: null,
      });
    });
  });

  it('duplicates a question right below the original', async () => {
    mockedGet.mockResolvedValue({ data: wireSurvey });
    mockedPost.mockResolvedValueOnce({ data: { id: 'q1-copy' } });
    mockedPut.mockResolvedValueOnce({ data: [] });
    renderScreen();
    await screen.findByDisplayValue('first');

    const [firstDuplicate] = screen.getAllByRole('button', { name: 'duplicate' });
    fireEvent.click(firstDuplicate!);

    await waitFor(() => {
      expect(mockedPut).toHaveBeenCalledWith('/api/community/surveys/srv-1/questions/order/', {
        question_ids: ['q1', 'q1-copy', 'q2'],
      });
    });
    expect(mockedPost).toHaveBeenCalledWith(
      '/api/community/surveys/srv-1/questions/',
      expect.objectContaining({ label: 'first' }),
    );
  });

  it('creates one copy when duplicate is double-clicked', async () => {
    mockedGet.mockResolvedValue({ data: wireSurvey });
    mockedPost.mockResolvedValueOnce({ data: { id: 'q1-copy' } });
    mockedPut.mockResolvedValueOnce({ data: [] });
    renderScreen();
    await screen.findByDisplayValue('first');

    const [firstDuplicate] = screen.getAllByRole('button', { name: 'duplicate' });
    fireEvent.click(firstDuplicate!);
    fireEvent.click(firstDuplicate!);

    await waitFor(() => {
      expect(mockedPut).toHaveBeenCalledTimes(1);
    });
    expect(mockedPost).toHaveBeenCalledTimes(1);
  });

  it('keeps questions editable after the poll is finalized', async () => {
    mockedGet.mockResolvedValue({
      data: {
        ...wireSurvey,
        poll_result: {
          id: 'pr-1',
          winning_datetime: '2026-11-01T18:00:00Z',
          finalized_by_id: null,
          finalized_at: '2026-10-30T18:00:00Z',
        },
      },
    });
    renderScreen();
    const input = await screen.findByDisplayValue('first');

    expect(screen.getByText('this poll has been finalized')).toBeInTheDocument();
    expect(input).toBeEnabled();
    expect(screen.getByRole('button', { name: '+ add question' })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'delete' })).toHaveLength(2);
  });

  it('keeps a just-edited label when the condition is changed right after', async () => {
    mockedGet.mockResolvedValue({
      data: {
        ...wireSurvey,
        questions: [
          {
            id: 'q1',
            label: 'first',
            field_type: 'radio',
            options: ['yes', 'no'],
            required: false,
            display_order: 0,
          },
          { id: 'q2', label: 'second', field_type: 'text', required: false, display_order: 1 },
        ],
      },
    });
    mockedPatch.mockResolvedValue({ data: {} });
    renderScreen();
    const input = await screen.findByDisplayValue('second');

    fireEvent.change(input, { target: { value: 'second, renamed' } });
    fireEvent.blur(input);
    fireEvent.click(screen.getByRole('checkbox', { name: 'only show when' }));

    await waitFor(() => {
      expect(mockedPatch).toHaveBeenCalledTimes(2);
    });
    expect(mockedPatch).toHaveBeenLastCalledWith(
      '/api/community/surveys/srv-1/questions/q2/',
      expect.objectContaining({
        label: 'second, renamed',
        show_if: { question_id: 'q1', operator: 'equals', value: 'yes' },
      }),
    );
  });
});
