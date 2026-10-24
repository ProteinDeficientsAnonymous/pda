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
  anonymous: false,
  confirmationMessage: '',
  opensAt: null,
  closesAt: null,
  maxResponses: null,
  responseCount: 0,
  linkedEventId: null,
  feedbackEventType: '',
  questions: [],
  myResponseId: null,
  myAnswers: null,
  pollResult: null,
};

function fieldError(code: string, field: string) {
  return new AxiosError('Request failed', 'ERR', undefined, undefined, {
    status: 400,
    data: { detail: [{ code, field }] },
  } as AxiosResponse);
}

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
        anonymous: false,
        confirmationMessage: '',
        opensAt: null,
        closesAt: null,
        maxResponses: null,
        linkedEventId: 'evt-1',
        feedbackEventType: '',
      });
    });
    expect(onClose).toHaveBeenCalled();
  });

  it('keeps a linked event that is not in the active list selectable', async () => {
    renderDialog({ linkedEventId: 'evt-past' });
    expect(screen.getByLabelText('linked event')).toHaveValue('evt-past');

    await userEvent.click(screen.getByRole('button', { name: 'save' }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({ linkedEventId: 'evt-past' }),
      );
    });
  });

  it('shows a slug collision as a field error', async () => {
    mutateAsync.mockRejectedValue(fieldError('survey.slug_already_exists', 'slug'));
    const { onClose } = renderDialog();
    await userEvent.click(screen.getByRole('button', { name: 'save' }));

    expect(await screen.findByText('a survey with that slug already exists')).toBeInTheDocument();
    expect(screen.getByLabelText('slug')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it('clears the slug field error once the slug changes', async () => {
    mutateAsync.mockRejectedValue(fieldError('survey.slug_already_exists', 'slug'));
    renderDialog();
    await userEvent.click(screen.getByRole('button', { name: 'save' }));

    const slug = await screen.findByLabelText('slug');
    expect(slug).toHaveAttribute('aria-invalid', 'true');

    await userEvent.type(slug, '-2');

    expect(slug).not.toHaveAttribute('aria-invalid');
    expect(screen.queryByText('a survey with that slug already exists')).not.toBeInTheDocument();
  });

  it('shows a linked event error on the dropdown, not the generic banner', async () => {
    mutateAsync.mockRejectedValue(fieldError('event.not_found', 'linked_event_id'));
    renderDialog({ linkedEventId: 'evt-1' });
    await userEvent.click(screen.getByRole('button', { name: 'save' }));

    expect(await screen.findByText('event not found')).toBeInTheDocument();
    const select = screen.getByLabelText('linked event');
    expect(select).toHaveAttribute('aria-invalid', 'true');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();

    await userEvent.selectOptions(select, '');
    expect(select).not.toHaveAttribute('aria-invalid');
  });

  it('falls back to a generic message when the failure carries no field error', async () => {
    mutateAsync.mockRejectedValue(new Error('network down'));
    const { onClose } = renderDialog();
    await userEvent.click(screen.getByRole('button', { name: 'save' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "couldn't save settings — try again",
    );
    expect(screen.getByLabelText('slug')).not.toHaveAttribute('aria-invalid');
    expect(onClose).not.toHaveBeenCalled();
  });

  it('blocks save when title is blank', async () => {
    renderDialog();
    await userEvent.clear(screen.getByLabelText('title'));
    await userEvent.click(screen.getByRole('button', { name: 'save' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('title and slug are required');
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it('saves anonymous and confirmation message edits', async () => {
    renderDialog();
    await userEvent.click(screen.getByLabelText(/anonymous responses/));
    await userEvent.type(screen.getByLabelText('confirmation message (optional)'), 'thanks!');
    await userEvent.click(screen.getByRole('button', { name: 'save' }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({ anonymous: true, confirmationMessage: 'thanks!' }),
      );
    });
  });

  it('disables one response per user while anonymous is checked', async () => {
    renderDialog();
    await userEvent.click(screen.getByLabelText(/anonymous responses/));
    expect(screen.getByLabelText(/one response per user/)).toBeDisabled();
  });

  it('sends the chosen feedback event type', async () => {
    renderDialog();
    const select = screen.getByLabelText('feedback survey for');
    expect(select).toHaveValue('');
    await userEvent.selectOptions(select, 'official events');
    await userEvent.click(screen.getByRole('button', { name: 'save' }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({ feedbackEventType: 'official' }),
      );
    });
  });

  it('seeds the feedback select from the survey and shows a taken error on it', async () => {
    mutateAsync.mockRejectedValue(fieldError('survey.feedback_type_taken', 'feedback_event_type'));
    renderDialog({ feedbackEventType: 'club' });
    const select = screen.getByLabelText('feedback survey for');
    expect(select).toHaveValue('club');
    await userEvent.click(screen.getByRole('button', { name: 'save' }));

    expect(await screen.findByText(/already/)).toBeInTheDocument();
    expect(select).toHaveAttribute('aria-invalid', 'true');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('locks the anonymous toggle once the survey has responses', () => {
    renderDialog({ responseCount: 3 });
    expect(screen.getByLabelText(/anonymous responses/)).toBeDisabled();
  });
});
