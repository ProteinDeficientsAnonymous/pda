import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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
});
