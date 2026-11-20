import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useEditablePage } from '@/api/content';
import { MembershipStatus } from '@/models/user';
import { apiError } from '@/test/apiError';
import { setAuthed, setUnauthed } from '@/test/auth';
import { makeUser } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import DonateScreen from './DonateScreen';
import VolunteerScreen from './VolunteerScreen';

vi.mock('@/api/content', () => ({
  useEditablePage: vi.fn(),
  useUpdateEditablePage: vi.fn(() => ({ mutateAsync: vi.fn() })),
}));

const mockUseEditablePage = vi.mocked(useEditablePage);

function failWith(status: number) {
  mockUseEditablePage.mockReturnValue({
    isPending: false,
    error: apiError(status),
    data: undefined,
  } as unknown as ReturnType<typeof useEditablePage>);
}

beforeEach(() => {
  vi.clearAllMocks();
  setUnauthed();
});

describe.each([
  { name: 'donate', Screen: DonateScreen, unlocks: 'see the donate page' },
  { name: 'volunteer', Screen: VolunteerScreen, unlocks: 'see volunteer opportunities' },
])('$name screen errors', ({ name, Screen, unlocks }) => {
  it('prompts signed-out visitors to log in and come back on 403', () => {
    failWith(403);
    renderWithProviders(<Screen />, { route: `/${name}` });

    expect(screen.getByText('log in to see this page')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'log in' })).toHaveAttribute(
      'href',
      `/login?redirect=${encodeURIComponent(`/${name}`)}`,
    );
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows the members-only notice to tentative members on 403', () => {
    setAuthed(makeUser({ membershipStatus: MembershipStatus.Tentative }));
    failWith(403);
    renderWithProviders(<Screen />, { route: `/${name}` });

    expect(screen.getByText(/you.+don.+t have access to this page yet/)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(unlocks))).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'log in' })).not.toBeInTheDocument();
  });

  it('keeps the load error for non-403 failures', () => {
    failWith(500);
    renderWithProviders(<Screen />, { route: `/${name}` });

    expect(screen.getByText(`couldn't load the ${name} page — try refreshing`)).toBeInTheDocument();
  });
});
