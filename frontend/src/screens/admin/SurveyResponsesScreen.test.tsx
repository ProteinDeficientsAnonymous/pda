import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

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
  { id: 'q-vibes', label: 'Vibes', fieldType: 'rating', options: [] },
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
    fieldType: 'rating',
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
}: {
  questions?: typeof QUESTIONS;
  summaries?: typeof SUMMARY_ROWS;
  summaryState?: Record<string, unknown>;
  responseCount?: number;
} = {}) {
  mockSurvey.mockReturnValue(
    mockQuery({ id: 'srv-1', title: 'feedback', questions, pollResult: null }),
  );
  mockResponses.mockReturnValue(
    mockQuery(
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

  it('should not render the summaries section when no question is summarizable', () => {
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

  it('should show a fallback while summaries are loading', () => {
    setup({ summaryState: { isPending: true, isSuccess: false, data: undefined } });
    expect(screen.getByText('loading summaries…')).toBeInTheDocument();
  });
});

describe('SurveyResponsesScreen csv download', () => {
  it('should request the csv when the button is clicked', async () => {
    setup();
    await userEvent.click(screen.getByRole('button', { name: 'download csv' }));
    expect(mockDownload).toHaveBeenCalledWith('srv-1');
  });

  it('should disable the button when there are no responses', () => {
    setup({ responseCount: 0 });
    expect(screen.getByRole('button', { name: 'download csv' })).toBeDisabled();
  });
});
