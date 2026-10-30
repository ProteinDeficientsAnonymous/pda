import { screen, within } from '@testing-library/react';
import { AxiosError, type AxiosResponse } from 'axios';
import { Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { renderWithProviders } from '@/test/render';

import EventSpeechScreen from './EventSpeechScreen';

vi.mock('@/api/client', () => ({
  setAuthBridge: vi.fn(),
  authClient: { post: vi.fn(), get: vi.fn() },
  apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

const UNSAVED_WALK = {
  event_title: 'Walk on the Hudson',
  official_kind: 'walk',
  saved: false,
  values: {
    facilitators: 'ann and bo',
    open_roles: ['greeter', 'photographer'],
    upcoming_events: ['potluck'],
    intro_question: '',
    front_walker: '',
    back_walker: '',
    walk_details: '',
  },
  html: '',
  updated_at: null,
  updated_by_name: null,
};

const SAVED_WALK = {
  ...UNSAVED_WALK,
  saved: true,
  values: { ...UNSAVED_WALK.values, walk_details: 'meet at the gate' },
  html: '<p>welcome, ann and bo</p><blockquote>pause here</blockquote>',
  updated_at: '2026-10-29T12:00:00Z',
  updated_by_name: 'Ann',
};

function renderScreen() {
  return renderWithProviders(
    <Routes>
      <Route path="/events/:id/speech" element={<EventSpeechScreen />} />
      <Route path="/events/:id" element={<div>event detail</div>} />
    </Routes>,
    { route: '/events/ev1/speech' },
  );
}

function httpError(status: number) {
  return new AxiosError('fail', 'ERR', undefined, undefined, {
    status,
    data: {},
  } as AxiosResponse);
}

beforeEach(() => {
  vi.mocked(apiClient.get).mockReset().mockResolvedValue({ data: UNSAVED_WALK });
});

describe('EventSpeechScreen', () => {
  it('shows the shared and walk blanks only, prefilled, with lists as textareas', async () => {
    renderScreen();

    expect(await screen.findByLabelText('facilitators')).toHaveValue('ann and bo');
    expect(screen.getByLabelText('front walker')).toBeInTheDocument();
    expect(screen.getByLabelText('back walker')).toBeInTheDocument();
    expect(screen.getByLabelText('walk details')).toBeInTheDocument();
    expect(screen.queryByLabelText('restaurant')).not.toBeInTheDocument();

    const roles = screen.getByLabelText('open roles');
    expect(roles.tagName).toBe('TEXTAREA');
    expect(roles).toHaveValue('greeter\nphotographer');
    expect(screen.getByLabelText('facilitators').tagName).toBe('INPUT');
  });

  it('shows the event title, keeping its casing', async () => {
    renderScreen();

    expect(await screen.findByText('Walk on the Hudson')).toBeInTheDocument();
  });

  it('styles the reading view for reading aloud', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: SAVED_WALK });
    renderScreen();

    const text = await screen.findByText('welcome, ann and bo');
    const container = text.closest('.prose')!;
    expect(container).toHaveClass('text-lg', 'break-words', '[overflow-wrap:anywhere]');
    expect(container.className).toContain('[&_blockquote]:border-yellow-400');
    expect(container.className).toContain('[&_blockquote]:text-sm');
    expect(container.className).toContain('[&_blockquote]:italic');
    expect(within(container as HTMLElement).queryByRole('button')).not.toBeInTheDocument();
  });

  it('explains a 403', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(httpError(403));
    renderScreen();

    expect(
      await screen.findByText("only this event's hosts can see its speech"),
    ).toBeInTheDocument();
  });

  it('explains a 404', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(httpError(404));
    renderScreen();

    expect(await screen.findByText('speeches are only for official events')).toBeInTheDocument();
  });
});
