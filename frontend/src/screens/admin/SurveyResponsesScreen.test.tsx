import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const toastError = vi.hoisted(() => vi.fn());
vi.mock('sonner', () => ({ toast: { error: toastError, success: vi.fn() } }));

import { QuestionType } from '@/api/questionTypes';
import {
  downloadSurveyResponsesCsv,
  useAdminSurvey,
  useSurveyPollTallies,
  useSurveyQuestionSummaries,
  useSurveyResponses,
} from '@/api/surveyAdmin';

import SurveyResponsesScreen from './SurveyResponsesScreen';

vi.mock('@/api/surveyAdmin', () => ({
  useAdminSurvey: vi.fn(),
  useSurveyResponses: vi.fn(),
  useSurveyPollTallies: vi.fn(),
  useSurveyQuestionSummaries: vi.fn(),
  useFinalizeSurveyPoll: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useDeleteSurveyResponse: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  downloadSurveyResponsesCsv: vi.fn(),
}));

const mockSurvey = vi.mocked(useAdminSurvey);
const mockResponses = vi.mocked(useSurveyResponses);
const mockTallies = vi.mocked(useSurveyPollTallies);
const mockSummaries = vi.mocked(useSurveyQuestionSummaries);
const mockDownload = vi.mocked(downloadSurveyResponsesCsv);

interface Question {
  id: string;
  label: string;
  fieldType: string;
  options: string[];
}

interface SummaryRow {
  questionId: string;
  fieldType: string;
  counts: Record<string, number>;
  answered: number;
  mean: number | null;
}

const QUESTIONS: Question[] = [
  { id: 'q-colour', label: 'Colour', fieldType: 'radio', options: ['red', 'blue'] },
  { id: 'q-vibes', label: 'Vibes', fieldType: QuestionType.Stars, options: [] },
  { id: 'q-notes', label: 'Notes', fieldType: 'text', options: [] },
];

const SUMMARY_ROWS: SummaryRow[] = [
  {
    questionId: 'q-colour',
    fieldType: 'radio',
    counts: { red: 3, blue: 1 },
    answered: 4,
    mean: null,
  },
  {
    questionId: 'q-vibes',
    fieldType: QuestionType.Stars,
    counts: { '1': 0, '2': 1, '3': 0, '4': 0, '5': 1 },
    answered: 2,
    mean: 3.5,
  },
];

function mockQuery(data: unknown, overrides: Record<string, unknown> = {}) {
  return { isPending: false, isError: false, isSuccess: true, data, ...overrides } as never;
}

function setup({
  questions = QUESTIONS,
  summaries = SUMMARY_ROWS,
  summaryState = {},
  responseCount = 1,
  feedbackEventType = '',
  responses,
}: {
  questions?: typeof QUESTIONS;
  summaries?: typeof SUMMARY_ROWS;
  summaryState?: Record<string, unknown>;
  responseCount?: number;
  feedbackEventType?: string;
  responses?: unknown[];
} = {}) {
  mockSurvey.mockReturnValue(
    mockQuery({
      id: 'srv-1',
      title: 'feedback',
      slug: 'feedback',
      questions,
      pollResult: null,
      feedbackEventType,
    }),
  );
  mockResponses.mockReturnValue(
    mockQuery(
      responses ??
        Array.from({ length: responseCount }, (_, i) => ({
          id: `r-${String(i)}`,
          userId: 'u1',
          userName: 'ada',
          answers: { 'q-colour': { label: 'Colour', answer: 'red' } },
          submittedAt: '2026-04-20T12:00:00.000Z',
        })),
    ),
  );
  mockTallies.mockReturnValue(mockQuery([]));
  mockSummaries.mockReturnValue(mockQuery(summaries, summaryState));

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/admin/surveys/srv-1/responses']}>
        <Routes>
          <Route path="/admin/surveys/:id/responses" element={<SurveyResponsesScreen />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('SurveyResponsesScreen summaries', () => {
  it('should render option counts and shares for a choice question', () => {
    setup();
    const section = screen.getByText('question summaries').closest('section')!;
    const colour = within(section).getByText('colour').closest('div')!;
    const red = within(colour).getByText('red').closest('tr')!;
    expect(within(red).getByText('3')).toBeInTheDocument();
    expect(within(red).getByText('75%')).toBeInTheDocument();
    expect(within(colour).getByText('4 answered')).toBeInTheDocument();
  });

  it('should let long unbroken options wrap instead of widening the page', () => {
    setup();
    const section = screen.getByText('question summaries').closest('section')!;
    expect(within(section).getByRole('cell', { name: 'red' })).toHaveClass('wrap-anywhere');
  });

  it('should render the rating distribution with its mean', () => {
    setup();
    const section = screen.getByText('question summaries').closest('section')!;
    const vibes = within(section).getByText('vibes').closest('div')!;
    expect(within(vibes).getByText('2 answered · average 3.50')).toBeInTheDocument();
    const five = within(vibes).getByText('5').closest('tr')!;
    expect(within(five).getByText('1')).toBeInTheDocument();
  });

  it('should share checkbox options across respondents, not across selections', () => {
    setup({
      questions: [
        {
          id: 'q-food',
          label: 'Food',
          fieldType: 'checkbox',
          options: ['kale', 'tofu'],
        },
      ],
      summaries: [
        {
          questionId: 'q-food',
          fieldType: 'checkbox',
          counts: { kale: 2, tofu: 1 },
          answered: 2,
          mean: null,
        },
      ],
    });
    const food = screen.getByText('food').closest('div')!;
    const kale = within(food).getByText('kale').closest('tr')!;
    const tofu = within(food).getByText('tofu').closest('tr')!;
    expect(within(kale).getByText('100%')).toBeInTheDocument();
    expect(within(tofu).getByText('50%')).toBeInTheDocument();
  });

  it('should keep the question option order for integer-like options', () => {
    setup({
      questions: [
        {
          id: 'q-year',
          label: 'Year',
          fieldType: 'select',
          options: ['2024', '2023', '2022'],
        },
      ],
      summaries: [
        {
          questionId: 'q-year',
          fieldType: 'select',
          counts: { '2024': 1, '2023': 2, '2022': 3 },
          answered: 6,
          mean: null,
        },
      ],
    });
    const year = screen.getByText('year').closest('div')!;
    const options = within(year)
      .getAllByRole('row')
      .slice(1)
      .map((tr) => tr.firstElementChild?.textContent);
    expect(options).toEqual(['2024', '2023', '2022']);
  });

  it('should not render the summaries section when the server returns no summaries', () => {
    mockSurvey.mockReturnValue(
      mockQuery({
        id: 'srv-1',
        title: 'feedback',
        questions: [QUESTIONS[2]],
        pollResult: null,
      }),
    );
    mockResponses.mockReturnValue(mockQuery([]));
    mockTallies.mockReturnValue(mockQuery([]));
    mockSummaries.mockReturnValue(mockQuery([]));
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/admin/surveys/srv-1/responses']}>
          <Routes>
            <Route path="/admin/surveys/:id/responses" element={<SurveyResponsesScreen />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.queryByText('question summaries')).not.toBeInTheDocument();
  });

  it('should hold the summaries section back while summaries are loading', () => {
    setup({ summaryState: { isPending: true, isSuccess: false, data: undefined } });
    expect(screen.queryByText('question summaries')).not.toBeInTheDocument();
  });

  it('should show an error message when summaries fail to load', () => {
    setup({ summaryState: { isError: true, isSuccess: false, data: undefined } });
    expect(screen.getByText("couldn't load summaries")).toBeInTheDocument();
  });

  it('should bucket answers outside the current options after the known ones', () => {
    setup({
      summaries: [
        {
          questionId: 'q-colour',
          fieldType: 'radio',
          counts: { red: 1, blue: 0, green: 1 },
          answered: 2,
          mean: null,
        },
      ],
    });
    const colour = screen.getByText('colour').closest('div')!;
    const options = within(colour)
      .getAllByRole('row')
      .slice(1)
      .map((tr) => tr.firstElementChild?.textContent);
    expect(options).toEqual(['red', 'blue', 'green']);
  });
});

describe('SurveyResponsesScreen csv download', () => {
  it('should request the csv when the button is clicked', async () => {
    setup();
    await userEvent.click(screen.getByRole('button', { name: 'download csv' }));
    expect(mockDownload).toHaveBeenCalledWith('srv-1', 'feedback');
  });

  it('should toast when the download fails', async () => {
    mockDownload.mockRejectedValueOnce(new Error('boom'));
    setup();
    await userEvent.click(screen.getByRole('button', { name: 'download csv' }));
    expect(toastError).toHaveBeenCalledWith("couldn't download csv");
    expect(screen.getByRole('button', { name: 'download csv' })).toBeEnabled();
  });

  it('should disable the button when there are no responses', () => {
    setup({ responseCount: 0 });
    expect(screen.getByRole('button', { name: 'download csv' })).toBeDisabled();
  });
});

function feedbackResponse(id: string, answer: string, event: { id: string; title: string } | null) {
  return {
    id,
    userId: null,
    userName: null,
    answers: { 'q-colour': { label: 'Colour', answer } },
    submittedAt: '2026-04-20T00:00:00.000Z',
    eventId: event?.id ?? null,
    eventTitle: event?.title ?? null,
    eventStart: event ? '2026-04-18T18:00:00.000Z' : null,
  };
}

describe('SurveyResponsesScreen event filter', () => {
  const potluck = { id: 'ev-1', title: 'Potluck' };
  const picnic = { id: 'ev-2', title: 'Picnic' };
  const rows = [
    feedbackResponse('r-1', 'crimson', potluck),
    feedbackResponse('r-2', 'azure', picnic),
    feedbackResponse('r-3', 'orphaned', null),
  ];

  it('should not render the filter for a regular survey', () => {
    setup({ responses: rows });
    expect(screen.queryByRole('combobox', { name: 'event' })).not.toBeInTheDocument();
  });

  it('should list distinct events with their dates for a feedback survey', () => {
    setup({ feedbackEventType: 'community', responses: [...rows, rows[0]] });
    const options = within(screen.getByRole('combobox', { name: 'event' })).getAllByRole('option');
    expect(options.map((o) => o.textContent)).toEqual([
      'all events',
      'potluck · apr 18',
      'picnic · apr 18',
    ]);
  });

  it('should hide other events rows once an event is selected', async () => {
    setup({ feedbackEventType: 'community', responses: rows });
    expect(screen.getByText('orphaned')).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'event' }), 'ev-1');

    expect(screen.getByText('crimson')).toBeInTheDocument();
    expect(screen.queryByText('azure')).not.toBeInTheDocument();
    expect(screen.queryByText('orphaned')).not.toBeInTheDocument();
  });

  it('should show every row again on all events', async () => {
    setup({ feedbackEventType: 'community', responses: rows });
    const select = screen.getByRole('combobox', { name: 'event' });
    await userEvent.selectOptions(select, 'ev-2');
    await userEvent.selectOptions(select, '');

    expect(screen.getByText('crimson')).toBeInTheDocument();
    expect(screen.getByText('orphaned')).toBeInTheDocument();
  });

  it('should show an event column for a feedback survey only', () => {
    const { unmount } = setup({ feedbackEventType: 'community', responses: rows });
    expect(screen.getByRole('columnheader', { name: 'event' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: 'potluck' })).toBeInTheDocument();
    unmount();

    setup({ responses: rows });
    expect(screen.queryByRole('columnheader', { name: 'event' })).not.toBeInTheDocument();
  });

  it('should pin the event as the first column so it stays visible while scrolling', () => {
    setup({ feedbackEventType: 'community', responses: rows });
    const header = screen.getByRole('columnheader', { name: 'event' });
    expect(header.parentElement?.firstElementChild).toBe(header);
    expect(header).toHaveClass('sticky', 'left-0');
    expect(screen.getByRole('cell', { name: 'potluck' })).toHaveClass('sticky', 'left-0');
  });

  it('should show x of y responses and scope summaries once an event is selected', async () => {
    setup({ feedbackEventType: 'community', responses: rows });
    expect(screen.getByText('3 responses')).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'event' }), 'ev-1');

    expect(screen.getByText('1 of 3 responses')).toBeInTheDocument();
    expect(mockSummaries).toHaveBeenLastCalledWith('srv-1', 'ev-1');
  });

  it('should not render the filter when no response has an event', () => {
    setup({ feedbackEventType: 'community', responses: [feedbackResponse('r-9', 'x', null)] });
    expect(screen.queryByRole('combobox', { name: 'event' })).not.toBeInTheDocument();
  });
});
