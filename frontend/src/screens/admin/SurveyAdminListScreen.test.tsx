import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AxiosError, type AxiosResponse } from 'axios';
import type * as RouterDom from 'react-router-dom';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { SurveySummary } from '@/api/surveyAdmin';

import SurveyAdminListScreen from './SurveyAdminListScreen';

const toastSuccess = vi.fn();
const createMutateAsync = vi.fn();
const navigate = vi.fn();

const surveys: SurveySummary[] = [
  {
    id: 's1',
    title: 'spring potluck',
    slug: 'spring-potluck',
    visibility: 'members_only',
    isActive: true,
    linkedEventId: null,
    createdAt: '2026-03-01T00:00:00Z',
    responseCount: 2,
  },
  {
    id: 's2',
    title: 'summer picnic',
    slug: 'summer-picnic',
    visibility: 'public',
    isActive: false,
    linkedEventId: null,
    createdAt: '2026-04-01T00:00:00Z',
    responseCount: 0,
  },
];

vi.mock('sonner', () => ({
  toast: {
    success: (m: string) => {
      toastSuccess(m);
    },
    error: vi.fn(),
  },
}));

vi.mock('@/api/surveyAdmin', () => ({
  useAdminSurveys: () => ({ data: surveys, isPending: false, isError: false }),
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
  render(
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
