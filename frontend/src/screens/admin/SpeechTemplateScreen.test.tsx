import { fireEvent, screen, waitFor } from '@testing-library/react';
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
