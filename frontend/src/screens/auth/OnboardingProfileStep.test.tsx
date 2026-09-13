import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';
import { makeUser } from '@/test/fixtures';

import { OnboardingProfileStep } from './OnboardingProfileStep';

vi.mock('@/auth/store', () => ({
  useAuthStore: vi.fn(),
}));

// AvatarUpload pulls in image-crop/canvas machinery we don't need here; stub it.
vi.mock('@/screens/settings/AvatarUpload', () => ({
  AvatarUpload: () => <div data-testid="avatar-upload" />,
}));

const baseUser = makeUser({
  id: 'u1',
  phoneNumber: '+15551234567',
  firstName: 'Tester',
  lastName: '',
  fullName: 'Tester',
  email: 'tester@example.com',
});

describe('OnboardingProfileStep', () => {
  const updateProfile = vi.fn();
  const onDone = vi.fn();

  function mockStore(user: User) {
    vi.mocked(useAuthStore).mockImplementation((selector) =>
      selector({ user, updateProfile } as never),
    );
  }

  beforeEach(() => {
    updateProfile.mockReset();
    onDone.mockReset();
    updateProfile.mockResolvedValue(undefined);
    mockStore(baseUser);
  });

  it('marks veganniversary seen without other fields when "do this later" is clicked', async () => {
    render(<OnboardingProfileStep onDone={onDone} />);
    await userEvent.click(screen.getByRole('button', { name: /do this later/i }));
    expect(updateProfile).toHaveBeenCalledWith({ hasSeenVeganniversary: true });
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it('saves a non-empty bio then finishes when "done" is clicked', async () => {
    render(<OnboardingProfileStep onDone={onDone} />);
    await userEvent.type(screen.getByLabelText(/^bio$/i), 'i love tofu');
    await userEvent.click(screen.getByRole('button', { name: /^done$/i }));
    expect(updateProfile).toHaveBeenCalledWith({
      bio: 'i love tofu',
      hasSeenVeganniversary: true,
    });
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it('marks veganniversary seen when bio and pronouns are left empty', async () => {
    render(<OnboardingProfileStep onDone={onDone} />);
    await userEvent.click(screen.getByRole('button', { name: /^done$/i }));
    expect(updateProfile).toHaveBeenCalledWith({ hasSeenVeganniversary: true });
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it('saves non-empty pronouns then finishes when "done" is clicked', async () => {
    render(<OnboardingProfileStep onDone={onDone} />);
    await userEvent.type(screen.getByLabelText(/pronouns/i), 'they/them');
    await userEvent.click(screen.getByRole('button', { name: /^done$/i }));
    expect(updateProfile).toHaveBeenCalledWith({
      pronouns: 'they/them',
      hasSeenVeganniversary: true,
    });
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it('shows privacy toggles including show birthday', () => {
    render(<OnboardingProfileStep onDone={onDone} />);
    expect(screen.getByText(/show birthday on my profile/i)).toBeInTheDocument();
    expect(screen.getByText(/show phone on my profile/i)).toBeInTheDocument();
    expect(screen.getByText(/show email on my profile/i)).toBeInTheDocument();
  });

  it('shows a birthday field with an edit control', () => {
    render(<OnboardingProfileStep onDone={onDone} />);
    expect(screen.getByText(/^birthday$/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /edit birthday/i })).toBeInTheDocument();
  });

  it('shows a veganniversary field without the month/year hint until editing', async () => {
    const user = userEvent.setup();
    render(<OnboardingProfileStep onDone={onDone} />);
    expect(screen.getByText(/^veganniversary$/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /edit veganniversary/i })).toBeInTheDocument();
    expect(
      screen.queryByText(
        /the exact date isn't required, but please let us know at least the month and year/i,
      ),
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /edit veganniversary/i }));
    expect(
      screen.getByText(
        /the exact date isn't required, but please let us know at least the month and year/i,
      ),
    ).toBeInTheDocument();
  });

  it('shows veganniversary privacy toggles in the privacy section', () => {
    render(<OnboardingProfileStep onDone={onDone} />);
    expect(
      screen.getByRole('switch', { name: /show veganniversary on my profile/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('switch', { name: /show my name in veganniversary shout out emails/i }),
    ).not.toBeChecked();
  });

  it('shows the "photo added" confirmation once a profile photo exists', () => {
    mockStore({ ...baseUser, profilePhotoUrl: 'https://example.com/p.png' });
    render(<OnboardingProfileStep onDone={onDone} />);
    expect(screen.getByText(/photo added/i)).toBeInTheDocument();
  });

  it('does not show the "photo added" confirmation when there is no photo', () => {
    render(<OnboardingProfileStep onDone={onDone} />);
    expect(screen.queryByText(/photo added/i)).not.toBeInTheDocument();
  });
});
