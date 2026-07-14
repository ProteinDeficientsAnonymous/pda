import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { MemberProfile } from '@/api/users';

import MemberProfileScreen from './MemberProfileScreen';

const useMemberProfileMock = vi.hoisted(() => vi.fn());

vi.mock('@/api/users', () => ({
  useMemberProfile: useMemberProfileMock,
}));

const BASE: MemberProfile = {
  id: 'u1',
  fullName: 'Alex',
  nickname: '',
  phoneNumber: '',
  email: '',
  bio: '',
  pronouns: '',
  birthday: null,
  profilePhotoUrl: '',
  loginLinkRequested: false,
};

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={['/members/u1']}>
      <Routes>
        <Route path="/members/:userId" element={<MemberProfileScreen />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('MemberProfileScreen', () => {
  it('shows pronouns when the member has them set', () => {
    useMemberProfileMock.mockReturnValue({
      data: { ...BASE, pronouns: 'they/them' },
      isPending: false,
      isError: false,
    });
    renderScreen();
    expect(screen.getByText('they/them')).toBeInTheDocument();
  });

  it('omits pronouns when the member has none set', () => {
    useMemberProfileMock.mockReturnValue({ data: BASE, isPending: false, isError: false });
    renderScreen();
    expect(screen.queryByText('they/them')).not.toBeInTheDocument();
  });

  it('shows the nickname beneath the name when set', () => {
    useMemberProfileMock.mockReturnValue({
      data: { ...BASE, nickname: 'Birdie' },
      isPending: false,
      isError: false,
    });
    renderScreen();
    expect(screen.getByText('"Birdie"')).toBeInTheDocument();
  });

  it('omits the nickname line when the member has none set', () => {
    useMemberProfileMock.mockReturnValue({ data: BASE, isPending: false, isError: false });
    renderScreen();
    expect(screen.queryByText(/^".*"$/)).not.toBeInTheDocument();
  });
});
