import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AxiosError, type AxiosResponse } from 'axios';
import { Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { Code } from '@/api/validationCodes';
import { renderWithProviders } from '@/test/render';

import EventSpeechScreen from './EventSpeechScreen';

vi.mock('@/api/client', () => ({
  setAuthBridge: vi.fn(),
  authClient: { post: vi.fn(), get: vi.fn() },
  apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

const UNSAVED_WALK = {
  event_title: 'Walk on the Hudson',
  event_format: 'walk',
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

function httpError(status: number, code?: string) {
  return new AxiosError('fail', 'ERR', undefined, undefined, {
    status,
    data: code ? { detail: [{ code, field: null }] } : {},
  } as AxiosResponse);
}

beforeEach(() => {
  vi.spyOn(window, 'scrollTo').mockImplementation(() => undefined);
  vi.mocked(apiClient.get).mockReset().mockResolvedValue({ data: UNSAVED_WALK });
  vi.mocked(apiClient.put).mockReset().mockResolvedValue({ data: SAVED_WALK });
});

describe('EventSpeechScreen', () => {
  it('shows the shared and walk blanks only, prefilled, with lists as textareas', async () => {
    renderScreen();

    expect(await screen.findByLabelText('facilitators')).toHaveValue('ann and bo');
    expect(screen.getByLabelText('front walker')).toBeInTheDocument();
    expect(screen.getByLabelText('back walker')).toBeInTheDocument();
    expect(screen.getByText("who's the walk leader?")).toBeInTheDocument();
    expect(screen.getByText("who's in the back of the group?")).toBeInTheDocument();
    expect(screen.getByLabelText('walk details')).toBeInTheDocument();
    expect(screen.queryByLabelText('restaurant')).not.toBeInTheDocument();

    const roles = screen.getByLabelText('open roles');
    expect(roles.tagName).toBe('TEXTAREA');
    expect(roles).toHaveValue('greeter\nphotographer');
    expect(screen.getByLabelText('facilitators').tagName).toBe('INPUT');
  });

  it('lets the host edit text and list blanks', async () => {
    const user = userEvent.setup();
    renderScreen();

    const facilitators = await screen.findByLabelText('facilitators');
    await user.clear(facilitators);
    await user.type(facilitators, 'cy');
    expect(facilitators).toHaveValue('cy');

    const roles = screen.getByLabelText('open roles');
    await user.type(roles, '{enter}driver');
    expect(roles).toHaveValue('greeter\nphotographer\ndriver');
  });

  it('shows an empty field for a blank with no prefill', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { ...UNSAVED_WALK, event_format: 'restaurant' },
    });
    renderScreen();

    expect(await screen.findByLabelText('restaurant')).toHaveValue('');
    expect(screen.queryByLabelText('walk details')).not.toBeInTheDocument();
  });

  it('shows the event title, keeping its casing', async () => {
    renderScreen();

    expect(await screen.findByText('Walk on the Hudson')).toBeInTheDocument();
  });

  it('opens a saved speech with no format in the form with the format picker', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { ...SAVED_WALK, event_format: null, html: '' },
    });
    renderScreen();

    expect(await screen.findByRole('radiogroup', { name: 'event format' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'edit' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'cancel' })).not.toBeInTheDocument();
  });

  it('asks for walk or restaurant first when the event has no format', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { ...UNSAVED_WALK, event_format: null },
    });
    const user = userEvent.setup();
    renderScreen();

    const choice = await screen.findByRole('radiogroup', { name: 'event format' });
    expect(screen.queryByLabelText('front walker')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'save' })).toBeDisabled();

    await user.click(within(choice).getByLabelText('restaurant'));
    expect(
      screen.getByLabelText('restaurant', { selector: 'input:not([type=radio])' }),
    ).toBeVisible();
    expect(screen.queryByLabelText('front walker')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'save' }));

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalled();
    });
    const body = vi.mocked(apiClient.put).mock.calls[0]?.[1] as { event_format: string };
    expect(body.event_format).toBe('restaurant');
  });

  it('saves trimmed values with list items split per line and switches to reading', async () => {
    const user = userEvent.setup();
    renderScreen();

    const details = await screen.findByLabelText('walk details');
    await user.type(details, 'meet at the gate');
    const roles = screen.getByLabelText('open roles');
    await user.clear(roles);
    await user.type(roles, ' greeter {Enter}{Enter}  scribe');
    await user.click(screen.getByRole('button', { name: 'save' }));

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalled();
    });
    const [url, body] = vi.mocked(apiClient.put).mock.calls[0] as [
      string,
      { values: Record<string, unknown>; event_format?: string },
    ];
    expect(url).toBe('/api/community/events/ev1/speech/');
    expect(body.event_format).toBeUndefined();
    expect(body.values.walk_details).toBe('meet at the gate');
    expect(body.values.open_roles).toEqual(['greeter', 'scribe']);
    expect(body.values).not.toHaveProperty('restaurant');

    expect(await screen.findByText('welcome, ann and bo')).toBeInTheDocument();
    expect(screen.queryByLabelText('facilitators')).not.toBeInTheDocument();
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
  });

  it('reads a saved speech and reopens the form from the edit button', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: SAVED_WALK });
    const user = userEvent.setup();
    renderScreen();

    expect(await screen.findByText('welcome, ann and bo')).toBeInTheDocument();
    expect(screen.getByText('updated by Ann'.toLowerCase())).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'edit' }));

    expect(screen.getByLabelText('walk details')).toHaveValue('meet at the gate');
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

  it('zooms the reading view in and out within bounds and remembers the size', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: SAVED_WALK });
    const user = userEvent.setup();
    const { unmount } = renderScreen();

    const text = await screen.findByText('welcome, ann and bo');
    const zoomed = text.closest('.prose')!.parentElement!;
    const zoomIn = screen.getByRole('button', { name: 'zoom in' });
    const zoomOut = screen.getByRole('button', { name: 'zoom out' });
    expect(zoomed.style.zoom).toBe('1');
    expect(zoomOut).toBeDisabled();

    await user.click(zoomIn);
    expect(zoomed.style.zoom).toBe('1.25');
    expect(zoomOut).toBeEnabled();

    for (let i = 0; i < 5; i++) await user.click(zoomIn);
    expect(zoomed.style.zoom).toBe('2');
    expect(zoomIn).toBeDisabled();

    await user.click(zoomOut);
    expect(zoomed.style.zoom).toBe('1.75');
    unmount();

    renderScreen();
    const reloaded = await screen.findByText('welcome, ann and bo');
    expect(reloaded.closest('.prose')!.parentElement!.style.zoom).toBe('1.75');
  });

  it('ignores an invalid stored zoom', async () => {
    localStorage.setItem('pda-speech-zoom', 'huge');
    vi.mocked(apiClient.get).mockResolvedValue({ data: SAVED_WALK });
    renderScreen();

    const text = await screen.findByText('welcome, ann and bo');
    expect(text.closest('.prose')!.parentElement!.style.zoom).toBe('1');
  });

  it('hides the zoom buttons while editing', async () => {
    renderScreen();

    expect(await screen.findByLabelText('facilitators')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'zoom in' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'zoom out' })).not.toBeInTheDocument();
  });

  it('explains a hosts-only error', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(httpError(403, Code.Speech.HostsOnly));
    renderScreen();

    expect(
      await screen.findByText(
        "only this event's hosts and event managers can see or edit its speech",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'back to event' })).toBeInTheDocument();
  });

  it('explains a non-official event', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(httpError(404, Code.Speech.OfficialEventRequired));
    renderScreen();

    expect(await screen.findByText('speeches are only for official events')).toBeInTheDocument();
  });

  it('shows a load error for an uncoded failure', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(httpError(500));
    renderScreen();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "couldn't load this speech — try refreshing",
    );
  });

  it('shows a save error and stays on the form', async () => {
    vi.mocked(apiClient.put).mockRejectedValue(httpError(500));
    const user = userEvent.setup();
    renderScreen();

    await user.click(await screen.findByRole('button', { name: 'save' }));

    expect(await screen.findByRole('alert')).toHaveTextContent("couldn't save");
    expect(screen.getByLabelText('facilitators')).toBeInTheDocument();
  });
});
