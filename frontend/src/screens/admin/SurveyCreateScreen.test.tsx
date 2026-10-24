import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AxiosError, type AxiosResponse } from 'axios';
import type * as RouterDom from 'react-router-dom';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import SurveyCreateScreen from './SurveyCreateScreen';

const createMutateAsync = vi.fn();
const navigate = vi.fn();

vi.mock('@/api/surveyAdmin', () => ({
  useCreateSurvey: () => ({ mutateAsync: createMutateAsync, isPending: false }),
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
      <SurveyCreateScreen />
    </MemoryRouter>,
  );
}

async function fillForm() {
  await userEvent.type(screen.getByLabelText('title'), 'retreat a');
  await userEvent.type(screen.getByLabelText('slug'), 'retreat-a');
  await userEvent.selectOptions(screen.getByLabelText('linked event'), 'evt-1');
}

beforeEach(() => {
  createMutateAsync.mockReset();
  createMutateAsync.mockResolvedValue({ id: 's-new' });
  navigate.mockReset();
});

describe('SurveyCreateScreen', () => {
  it('renders every survey field inline on the page', () => {
    renderScreen();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByLabelText('title')).toBeInTheDocument();
    expect(screen.getByLabelText('description (optional)')).toBeInTheDocument();
    expect(screen.getByLabelText('slug')).toBeInTheDocument();
    expect(screen.getByLabelText('visibility')).toBeInTheDocument();
    expect(screen.getByText('opens at')).toBeInTheDocument();
    expect(screen.getByText('closes at')).toBeInTheDocument();
    expect(screen.getByLabelText('max responses')).toBeInTheDocument();
  });

  it('links cancel back to the survey list', () => {
    renderScreen();
    expect(screen.getByRole('link', { name: 'cancel' })).toHaveAttribute('href', '/admin/surveys');
    expect(screen.getByRole('link', { name: '← back to surveys' })).toHaveAttribute(
      'href',
      '/admin/surveys',
    );
  });

  it('requires a title and slug before submitting', async () => {
    renderScreen();
    await userEvent.click(screen.getByRole('button', { name: 'create' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('title and slug are required');
    expect(createMutateAsync).not.toHaveBeenCalled();
  });

  it('creates the survey and opens its builder', async () => {
    renderScreen();
    await fillForm();
    await userEvent.type(screen.getByLabelText('max responses'), '25');
    await userEvent.click(screen.getByRole('button', { name: 'create' }));

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/admin/surveys/s-new', { replace: true });
    });
    expect(createMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'retreat a',
        slug: 'retreat-a',
        linkedEventId: 'evt-1',
        maxResponses: 25,
        opensAt: null,
        closesAt: null,
      }),
    );
  });

  it('shows a slug collision inline on the slug field and clears it on change', async () => {
    createMutateAsync.mockRejectedValue(fieldError('survey.slug_already_exists', 'slug'));
    renderScreen();
    await fillForm();
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
    await fillForm();
    await userEvent.click(screen.getByRole('button', { name: 'create' }));

    expect(await screen.findByText('event not found')).toBeInTheDocument();
    expect(screen.getByLabelText('linked event')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows a taken feedback type inline on the select', async () => {
    createMutateAsync.mockRejectedValue(
      fieldError('survey.feedback_type_taken', 'feedback_event_type'),
    );
    renderScreen();
    await fillForm();
    await userEvent.selectOptions(screen.getByLabelText('feedback survey for'), 'official events');
    await userEvent.click(screen.getByRole('button', { name: 'create' }));

    expect(await screen.findByText(/already/)).toBeInTheDocument();
    expect(screen.getByLabelText('feedback survey for')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows a generic banner for a failure with no field error', async () => {
    createMutateAsync.mockRejectedValue(new Error('network down'));
    renderScreen();
    await fillForm();
    await userEvent.click(screen.getByRole('button', { name: 'create' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "couldn't create the survey — try again",
    );
    expect(screen.getByLabelText('slug')).not.toHaveAttribute('aria-invalid');
  });
});
