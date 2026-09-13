import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AxiosError, type AxiosResponse } from 'axios';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Survey } from '@/api/surveyAdmin';

import { SurveySettingsDialog } from './SurveySettingsDialog';

const mutateAsync = vi.fn();

vi.mock('@/api/surveyAdmin', () => ({
  useUpdateSurvey: () => ({ mutateAsync, isPending: false }),
}));

vi.mock('@/api/events', () => ({
  useEvents: () => ({
    data: [{ id: 'evt-1', title: 'Potluck', startDatetime: new Date('2026-10-01T18:00:00Z') }],
  }),
}));

const survey: Survey = {
  id: 's1',
  title: 'old title',
  description: 'about this survey',
  slug: 'old-slug',
  visibility: 'members_only',
  isActive: true,
  oneResponsePerUser: false,
  linkedEventId: null,
  questions: [],
  myResponseId: null,
  myAnswers: null,
  pollResult: null,
};

function renderDialog(overrides: Partial<Survey> = {}) {
  const onClose = vi.fn();
  render(<SurveySettingsDialog open onClose={onClose} survey={{ ...survey, ...overrides }} />);
  return { onClose };
}

describe('SurveySettingsDialog', () => {
  beforeEach(() => {
    mutateAsync.mockReset();
    mutateAsync.mockResolvedValue({ ...survey });
  });

  it('seeds fields from the survey and saves edits', async () => {
    const { onClose } = renderDialog();
    const title = screen.getByLabelText('title');
    expect(title).toHaveValue('old title');
    expect(screen.getByLabelText('slug')).toHaveValue('old-slug');
    expect(screen.getByLabelText('linked event')).toHaveValue('');

    await userEvent.clear(title);
    await userEvent.type(title, 'new title');
    await userEvent.selectOptions(screen.getByLabelText('visibility'), 'public');
    await userEvent.selectOptions(screen.getByLabelText('linked event'), 'evt-1');
    await userEvent.click(screen.getByLabelText('one response per user'));
    await userEvent.click(screen.getByRole('button', { name: 'save' }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        title: 'new title',
        description: 'about this survey',
        slug: 'old-slug',
        visibility: 'public',
        oneResponsePerUser: true,
        linkedEventId: 'evt-1',
      });
    });
    expect(onClose).toHaveBeenCalled();
  });

  it('keeps a linked event that is not in the active list selectable', () => {
    renderDialog({ linkedEventId: 'evt-past' });
    expect(screen.getByLabelText('linked event')).toHaveValue('evt-past');
  });

  it('shows a slug collision as a field error', async () => {
    mutateAsync.mockRejectedValue(
      new AxiosError('Request failed', 'ERR', undefined, undefined, {
        status: 400,
        data: { detail: [{ code: 'survey.slug_already_exists', field: 'slug' }] },
      } as AxiosResponse),
    );
    const { onClose } = renderDialog();
    await userEvent.click(screen.getByRole('button', { name: 'save' }));

    expect(await screen.findByText('a survey with that slug already exists')).toBeInTheDocument();
    expect(screen.getByLabelText('slug')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it('blocks save when title is blank', async () => {
    renderDialog();
    await userEvent.clear(screen.getByLabelText('title'));
    await userEvent.click(screen.getByRole('button', { name: 'save' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('title and slug are required');
    expect(mutateAsync).not.toHaveBeenCalled();
  });
});
