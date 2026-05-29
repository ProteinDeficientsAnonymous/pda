import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OnboardingProfileStep } from './OnboardingProfileStep';
import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';

vi.mock('@/auth/store', () => ({
  useAuthStore: vi.fn(),
}));

// AvatarUpload pulls in image-crop/canvas machinery we don't need here; stub it.
vi.mock('@/screens/settings/AvatarUpload', () => ({
  AvatarUpload: () => <div data-testid="avatar-upload" />,
}));

const baseUser: User = {
  id: 'u1',
  phoneNumber: '+15551234567',
  displayName: 'Tester',
  email: 'tester@example.com',
  bio: '',
  isSuperuser: false,
  isStaff: false,
  needsOnboarding: false,
  needsPasswordReset: false,
  showPhone: false,
  showEmail: false,
  weekStart: 'sunday',
  calendarFeedScope: 'all',
  profilePhotoUrl: '',
  photoUpdatedAt: null,
  roles: [],
};

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

  it('skips without saving when "do this later" is clicked', async () => {
    render(<OnboardingProfileStep onDone={onDone} />);
    await userEvent.click(screen.getByRole('button', { name: /do this later/i }));
    expect(updateProfile).not.toHaveBeenCalled();
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it('saves a non-empty bio then finishes when "done" is clicked', async () => {
    render(<OnboardingProfileStep onDone={onDone} />);
    await userEvent.type(screen.getByLabelText(/bio/i), 'i love tofu');
    await userEvent.click(screen.getByRole('button', { name: /^done$/i }));
    expect(updateProfile).toHaveBeenCalledWith({ bio: 'i love tofu' });
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it('finishes without calling updateProfile when bio is left empty', async () => {
    render(<OnboardingProfileStep onDone={onDone} />);
    await userEvent.click(screen.getByRole('button', { name: /^done$/i }));
    expect(updateProfile).not.toHaveBeenCalled();
    expect(onDone).toHaveBeenCalledTimes(1);
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
