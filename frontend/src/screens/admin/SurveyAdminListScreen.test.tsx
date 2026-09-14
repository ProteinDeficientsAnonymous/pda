import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AxiosError, type AxiosResponse } from 'axios';
import type * as RouterDom from 'react-router-dom';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { SurveySummary } from '@/api/surveyAdmin';
import { surveyStatus } from '@/models/survey';

import SurveyAdminListScreen from './SurveyAdminListScreen';

const toastSuccess = vi.fn();
const createMutateAsync = vi.fn();
const navigate = vi.fn();

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
  useCreateSurvey: () => ({ mutateAsync: createMutateAsync, isPending: false }),
  useDeleteSurvey: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock('@/api/events', () => ({
  useEvents: () => ({
    data: [{ id: 'evt-1', title: 'Potluck', startDatetime: new Date('2026-10-01T18:00:00Z') }],
  }),
}));

vi.mock('react-router-dom', async (importActual) => {
  const actual = await importActual<typeof RouterDom>();
  return { ...actual, useNavigate: () => navigate };
});

function fieldError(code: string, field: string) {
  return new AxiosError('Request failed', 'ERR', undefined, undefined, {
    status: 400,
    data: { detail: [{ code, field }] },
  } as AxiosResponse);
}

function renderScreen() {
  return render(
    <MemoryRouter>
      <SurveyAdminListScreen />
    </MemoryRouter>,
  );
}

async function openCreateDialog() {
  await userEvent.click(screen.getByRole('button', { name: 'new survey' }));
}

async function fillCreateForm() {
  await userEvent.type(screen.getByLabelText('title'), 'retreat a');
  await userEvent.type(screen.getByLabelText('slug'), 'retreat-a');
  await userEvent.selectOptions(screen.getByLabelText('linked event'), 'evt-1');
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

describe('SurveyAdminListScreen create dialog', () => {
  beforeEach(() => {
    createMutateAsync.mockReset();
    createMutateAsync.mockResolvedValue({ id: 's-new' });
    navigate.mockReset();
  });

  it('renders opens at, closes at, and max responses fields', async () => {
    renderScreen();
    await openCreateDialog();
    expect(screen.getByText('opens at')).toBeInTheDocument();
    expect(screen.getByText('closes at')).toBeInTheDocument();
    expect(screen.getByLabelText('max responses')).toBeInTheDocument();
  });

  it('submits max responses as a number, and null when left blank', async () => {
    renderScreen();
    await openCreateDialog();
    await fillCreateForm();
    await userEvent.type(screen.getByLabelText('max responses'), '25');
    await userEvent.click(screen.getByRole('button', { name: 'create' }));

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalled();
    });
    expect(createMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({ maxResponses: 25, opensAt: null, closesAt: null }),
    );
  });

  it('resets the form after a successful create', async () => {
    renderScreen();
    await openCreateDialog();
    await fillCreateForm();
    await userEvent.click(screen.getByRole('button', { name: 'create' }));

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalled();
    });

    await openCreateDialog();
    expect(screen.getByLabelText('title')).toHaveValue('');
    expect(screen.getByLabelText('slug')).toHaveValue('');
    expect(screen.getByLabelText('linked event')).toHaveValue('');
  });

  it('resets the form after cancelling', async () => {
    renderScreen();
    await openCreateDialog();
    await fillCreateForm();
    await userEvent.click(screen.getByRole('button', { name: 'cancel' }));

    await openCreateDialog();
    expect(screen.getByLabelText('title')).toHaveValue('');
    expect(screen.getByLabelText('slug')).toHaveValue('');
    expect(screen.getByLabelText('linked event')).toHaveValue('');
  });

  it('shows a slug collision inline on the slug field and clears it on change', async () => {
    createMutateAsync.mockRejectedValue(fieldError('survey.slug_already_exists', 'slug'));
    renderScreen();
    await openCreateDialog();
    await fillCreateForm();
    await userEvent.click(screen.getByRole('button', { name: 'create' }));

    expect(await screen.findByText('a survey with that slug already exists')).toBeInTheDocument();
    const slug = screen.getByLabelText('slug');
    expect(slug).toHaveAttribute('aria-invalid', 'true');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(navigate).not.toHaveBeenCalled();

    await userEvent.type(slug, '-2');
    expect(slug).not.toHaveAttribute('aria-invalid');
    expect(screen.queryByText('a survey with that slug already exists')).not.toBeInTheDocument();
  });

  it('shows a linked event error on the dropdown', async () => {
    createMutateAsync.mockRejectedValue(fieldError('event.not_found', 'linked_event_id'));
    renderScreen();
    await openCreateDialog();
    await fillCreateForm();
    await userEvent.click(screen.getByRole('button', { name: 'create' }));

    expect(await screen.findByText('event not found')).toBeInTheDocument();
    expect(screen.getByLabelText('linked event')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('still shows a generic banner for a failure with no field error', async () => {
    createMutateAsync.mockRejectedValue(new Error('network down'));
    renderScreen();
    await openCreateDialog();
    await fillCreateForm();
    await userEvent.click(screen.getByRole('button', { name: 'create' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "couldn't complete that action — try again",
    );
    expect(screen.getByLabelText('slug')).not.toHaveAttribute('aria-invalid');
  });
});
