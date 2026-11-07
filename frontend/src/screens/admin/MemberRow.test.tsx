import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import type { Member } from '@/api/users';
import { makeMember } from '@/test/fixtures';

import { MemberRow } from './MemberRow';

function renderRow(member: Member) {
  return render(
    <MemoryRouter>
      <MemberRow member={member} />
    </MemoryRouter>,
  );
}

describe('MemberRow pause badges', () => {
  it('shows a guidelines badge for an is_paused member', () => {
    renderRow(makeMember({ isPaused: true }));
    expect(screen.getByText('paused · guidelines')).toBeInTheDocument();
  });

  it('keeps an event rqmt paused member linked and not marked non-member', () => {
    renderRow(makeMember({ isMember: false, attendancePausedAt: new Date('2026-03-01') }));
    expect(screen.getByText('paused · event rqmt')).toBeInTheDocument();
    expect(screen.queryByText('non-member')).not.toBeInTheDocument();
    expect(screen.getByRole('link')).toHaveAttribute('href', '/admin/members/member-1');
  });
});
