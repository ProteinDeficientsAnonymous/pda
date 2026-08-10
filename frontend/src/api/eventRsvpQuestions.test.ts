import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { EventRsvpQuestion } from '@/models/event';
import { makeEvent } from '@/test/fixtures';

import { apiClient } from './client';
import {
  DRAFT_RSVP_QUESTION_ID_PREFIX,
  isDraftRsvpQuestionId,
  newRsvpQuestionId,
  syncEventRsvpQuestions,
} from './eventRsvpQuestions';
import { eventKeys } from './events';
import { queryClient } from './queryClient';

vi.mock('./client', async (importOriginal) => {
  const actual = (await importOriginal()) as {
    apiClient: Record<string, unknown>;
    [key: string]: unknown;
  };
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      put: vi.fn(),
    },
  };
});

const q = (
  partial: Partial<EventRsvpQuestion> & Pick<EventRsvpQuestion, 'id'>,
): EventRsvpQuestion => ({
  label: 'q',
  fieldType: 'textarea',
  options: [],
  required: false,
  ...partial,
});

describe('draft RSVP question ids', () => {
  it('should recognize and mint ids with the shared draft prefix', () => {
    expect(DRAFT_RSVP_QUESTION_ID_PREFIX).toBe('q-');
    expect(isDraftRsvpQuestionId(`${DRAFT_RSVP_QUESTION_ID_PREFIX}temp`)).toBe(true);
    expect(isDraftRsvpQuestionId('keep')).toBe(false);
    expect(newRsvpQuestionId().startsWith(DRAFT_RSVP_QUESTION_ID_PREFIX)).toBe(true);
  });
});

describe('syncEventRsvpQuestions', () => {
  beforeEach(() => {
    vi.mocked(apiClient.put).mockReset();
    queryClient.clear();
  });

  it('should replace all questions in one request', async () => {
    vi.mocked(apiClient.put).mockResolvedValue({
      data: [
        {
          id: 'keep',
          label: 'updated',
          field_type: 'textarea',
          options: [],
          required: false,
          display_order: 0,
        },
        {
          id: 'new',
          label: 'new',
          field_type: 'textarea',
          options: [],
          required: false,
          display_order: 1,
        },
      ],
    });

    const previous = [q({ id: 'keep', label: 'old' })];
    const draftId = `${DRAFT_RSVP_QUESTION_ID_PREFIX}temp-new`;
    const result = await syncEventRsvpQuestions(
      'evt',
      [q({ id: 'keep', label: 'updated' }), q({ id: draftId, label: 'new' })],
      previous,
    );

    expect(apiClient.put).toHaveBeenCalledWith('/api/community/events/evt/rsvp-questions/', {
      expected: [
        {
          id: 'keep',
          label: 'old',
          field_type: 'textarea',
          options: [],
          required: false,
        },
      ],
      questions: [
        {
          id: 'keep',
          label: 'updated',
          field_type: 'textarea',
          options: [],
          required: false,
        },
        {
          id: null,
          label: 'new',
          field_type: 'textarea',
          options: [],
          required: false,
        },
      ],
    });
    expect(result.map((question) => question.id)).toEqual(['keep', 'new']);
  });

  it('should patch cached event detail so the RSVP dialog sees synced questions', async () => {
    const eventId = 'evt-sync-cache';
    const slug = 'sync-cache-event';
    queryClient.setQueryData(
      eventKeys.detail(slug, true),
      makeEvent({ id: eventId, slug, rsvpQuestions: [] }),
    );
    vi.mocked(apiClient.put).mockResolvedValue({
      data: [
        {
          id: 'q1',
          label: 'how are you getting there?',
          field_type: 'select',
          options: ['transit'],
          required: true,
          display_order: 0,
        },
      ],
    });

    await syncEventRsvpQuestions(
      eventId,
      [q({ id: `${DRAFT_RSVP_QUESTION_ID_PREFIX}draft`, label: 'how are you getting there?' })],
      [],
    );

    expect(queryClient.getQueryData(eventKeys.detail(slug, true))).toMatchObject({
      rsvpQuestions: [
        {
          id: 'q1',
          label: 'how are you getting there?',
          fieldType: 'select',
          options: ['transit'],
          required: true,
        },
      ],
    });
  });
});
