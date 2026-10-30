import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { renderWithProviders } from '@/test/render';

import SpeechTemplateScreen from './SpeechTemplateScreen';

vi.mock('@/api/client', () => ({
  setAuthBridge: vi.fn(),
  authClient: { post: vi.fn(), get: vi.fn() },
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

const WIRE = {
  shared_pm: '',
  walk_pm: '',
  restaurant_pm: '',
  open_roles: ['host'],
  updated_at: '2026-10-29T00:00:00Z',
};

function renderScreen() {
  return renderWithProviders(<SpeechTemplateScreen />);
}

beforeEach(() => {
  vi.mocked(apiClient.get).mockReset().mockResolvedValue({ data: WIRE });
  vi.mocked(apiClient.patch).mockReset().mockResolvedValue({ data: WIRE });
});

describe('SpeechTemplateScreen', () => {
  it('shows the three section editors and the open roles textarea', async () => {
    renderScreen();

    expect(await screen.findByRole('heading', { name: 'everyone hears this' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'walks only' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'restaurants only' })).toBeInTheDocument();
    expect(screen.getByLabelText('open roles')).toHaveValue('host');
  });

  it('explains blockquote is for speaker notes', async () => {
    renderScreen();
    await screen.findByRole('heading', { name: 'walks only' });

    expect(screen.getByText(/blockquote for speaker notes/)).toBeInTheDocument();
  });

  it('inserts a blank from the + blank menu and saves walk_pm', async () => {
    const user = userEvent.setup();
    renderScreen();
    const walks = (await screen.findByRole('heading', { name: 'walks only' })).closest('section')!;

    await user.click(within(walks).getByRole('button', { name: '+ blank' }));
    await user.click(screen.getByRole('menuitem', { name: 'walk details' }));
    fireEvent.focusOut(walks);

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalled();
    });
    const [url, body] = vi.mocked(apiClient.patch).mock.calls[0] as [string, { walk_pm: string }];
    expect(url).toBe('/api/community/speech-template/');
    expect(body.walk_pm).toContain('"type":"speechBlank"');
    expect(body.walk_pm).toContain('"key":"walk_details"');
  });

  it('saves open roles one per line, dropping blanks', async () => {
    const user = userEvent.setup();
    renderScreen();
    const roles = await screen.findByLabelText('open roles');

    await user.clear(roles);
    await user.type(roles, 'a{enter}{enter}b');
    fireEvent.blur(roles);

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith('/api/community/speech-template/', {
        open_roles: ['a', 'b'],
      });
    });
  });
});
