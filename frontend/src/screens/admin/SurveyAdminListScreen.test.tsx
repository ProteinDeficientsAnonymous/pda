import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { SurveySummary } from '@/api/surveyAdmin';
import { surveyStatus } from '@/models/survey';

import SurveyAdminListScreen from './SurveyAdminListScreen';

const toastSuccess = vi.fn();

function makeSurvey(overrides: Partial<SurveySummary> = {}): SurveySummary {
  return {
    id: 's1',
    title: 'feedback',
    slug: 'feedback',
    visibility: 'members_only',
    isActive: true,
    opensAt: null,
    closesAt: null,
    maxResponses: null,
    linkedEventId: null,
    createdAt: '2026-01-01T00:00:00.000Z',
    responseCount: 0,
    ...overrides,
  };
}

const defaultSurveys: SurveySummary[] = [
  makeSurvey({
    id: 's1',
    title: 'spring potluck',
    slug: 'spring-potluck',
    createdAt: '2026-03-01T00:00:00Z',
    responseCount: 2,
  }),
  makeSurvey({
    id: 's2',
    title: 'summer picnic',
    slug: 'summer-picnic',
    visibility: 'public',
    isActive: false,
    createdAt: '2026-04-01T00:00:00Z',
  }),
];

let surveysMock: SurveySummary[] = defaultSurveys;

vi.mock('sonner', () => ({
  toast: {
    success: (m: string) => {
      toastSuccess(m);
    },
    error: vi.fn(),
  },
}));

vi.mock('@/api/surveyAdmin', () => ({
  useAdminSurveys: () => ({ data: surveysMock, isPending: false, isError: false }),
  useDeleteSurvey: () => ({ mutate: vi.fn(), isPending: false }),
}));

function renderScreen() {
  return render(
    <MemoryRouter>
      <SurveyAdminListScreen />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  surveysMock = defaultSurveys;
});

describe('surveyStatus', () => {
  const now = new Date('2026-06-01T12:00:00.000Z');

  it('is closed when inactive, regardless of window', () => {
    expect(surveyStatus(makeSurvey({ isActive: false }), { now })).toBe('closed');
  });

  it('is scheduled when opens_at is in the future', () => {
    const survey = makeSurvey({ opensAt: '2026-06-02T00:00:00.000Z' });
    expect(surveyStatus(survey, { now })).toBe('scheduled');
  });

  it('is closed once closes_at has passed', () => {
    const survey = makeSurvey({ closesAt: '2026-05-31T00:00:00.000Z' });
    expect(surveyStatus(survey, { now })).toBe('closed');
  });

  it('is capped once the response cap is reached', () => {
    const survey = makeSurvey({ maxResponses: 5, responseCount: 5 });
    expect(surveyStatus(survey, { now })).toBe('capped');
  });

  // A survey that is both scheduled and already at cap reads as scheduled —
  // the cap only becomes the reason it's shut once the window has opened.
  it('prefers scheduled over capped before the window opens', () => {
    const survey = makeSurvey({
      opensAt: '2026-06-02T00:00:00.000Z',
      maxResponses: 1,
      responseCount: 1,
    });
    expect(surveyStatus(survey, { now })).toBe('scheduled');
  });

  it('is active inside the window and under the cap', () => {
    const survey = makeSurvey({
      opensAt: '2026-05-01T00:00:00.000Z',
      closesAt: '2026-07-01T00:00:00.000Z',
      maxResponses: 10,
      responseCount: 3,
    });
    expect(surveyStatus(survey, { now })).toBe('active');
  });
});

describe('SurveyAdminListScreen badges', () => {
  it('shows a scheduled badge for a survey that has not opened yet', () => {
    surveysMock = [makeSurvey({ opensAt: '2999-01-01T00:00:00.000Z' })];
    renderScreen();
    expect(screen.getByText('scheduled')).toBeInTheDocument();
  });

  it('shows an at capacity badge for a survey at its response cap', () => {
    surveysMock = [makeSurvey({ maxResponses: 2, responseCount: 2 })];
    renderScreen();
    expect(screen.getByText('at capacity')).toBeInTheDocument();
  });

  it('shows an active badge for an open survey', () => {
    surveysMock = [makeSurvey()];
    renderScreen();
    expect(screen.getByText('active')).toBeInTheDocument();
  });
});

describe('SurveyAdminListScreen', () => {
  beforeEach(() => {
    toastSuccess.mockReset();
  });

  it('copies the participant link for the clicked row', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });

    renderScreen();

    expect(screen.getAllByRole('button', { name: 'copy link' })).toHaveLength(2);

    const row = screen.getByText('summer picnic').closest('article');
    if (!row) throw new Error('row not found');
    fireEvent.click(within(row).getByRole('button', { name: 'copy link' }));

    await vi.waitFor(() => {
      expect(toastSuccess).toHaveBeenCalledWith('link copied');
    });
    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/surveys/summer-picnic`);
  });
});

describe('SurveyAdminListScreen row meta', () => {
  beforeEach(() => {
    surveysMock = [makeSurvey({ createdAt: '2026-03-15T12:00:00Z', responseCount: 2 })];
  });

  it('shows visibility and the created date in lowercase', () => {
    renderScreen();
    expect(screen.getByText(/members only · 2 responses · mar 15, 2026/)).toBeInTheDocument();
  });
});
