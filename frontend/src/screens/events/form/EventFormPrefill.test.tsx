import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { QuestionType } from '@/api/questionTypes';
import { useAuthStore } from '@/auth/store';
import { EventType } from '@/models/event';
import { Permission } from '@/models/permissions';
import { makeUserWithPermissions } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

vi.mock('@/api/eventDescriptionTemplates', () => ({
  useEventDescriptionTemplates: () => ({
    data: { officialWalk: 'walk copy', officialNonWalk: 'non-walk copy' },
  }),
}));
vi.mock('@/api/officialEventDefaults', () => ({
  useOfficialEventDefaults: () => ({
    data: {
      cashappLink: 'https://cash.app/$pdanyc',
      rsvpQuestions: [
        { label: 'paid?', fieldType: QuestionType.Select, options: ['Yes'], required: true },
      ],
    },
  }),
}));
vi.mock('@/api/eventTags', () => ({ useEventTags: () => ({ data: [], isPending: false }) }));
vi.mock('./EventFormPhoto', () => ({ EventFormPhoto: () => null }));

import { EventForm } from './EventForm';

const START = new Date(2099, 2, 1, 10).toISOString();

const post = vi.spyOn(apiClient, 'post');

beforeEach(() => {
  post.mockReset().mockRejectedValue(new Error('stop after capturing the body'));
  useAuthStore.setState({
    user: makeUserWithPermissions([Permission.TagOfficialEvent]),
    status: 'authed',
  });
});

describe('EventForm prefilled as official', () => {
  it('sends the public, no-plus-ones fields official events require', async () => {
    renderWithProviders(
      <EventForm
        initial={{ title: 'march', eventType: EventType.Official, startDatetime: START }}
      />,
    );
    await userEvent.click(screen.getByRole('button', { name: 'publish' }));
    await waitFor(() => {
      expect(post).toHaveBeenCalled();
    });
    expect(post.mock.calls[0]?.[1]).toMatchObject({
      title: 'march',
      event_type: 'official',
      visibility: 'public',
      allow_plus_ones: false,
      rsvp_questions: [expect.objectContaining({ label: 'paid?' })],
    });
  });

  it('fills the official description template and cash app like toggling official does', async () => {
    renderWithProviders(<EventForm initial={{ eventType: EventType.Official }} />);
    await waitFor(() => {
      expect(screen.getByLabelText('description')).toHaveValue('walk copy');
    });
    expect(screen.getByLabelText('cash app')).toHaveValue('$pdanyc');
  });
});
