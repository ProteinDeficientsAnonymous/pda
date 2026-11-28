import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  type MemberAttendanceRow,
  useExtendAttendanceGrace,
} from '@/api/memberAttendanceAnalytics';

import { ExtendGraceButton } from './ExtendGraceButton';

vi.mock('@/api/memberAttendanceAnalytics', () => ({
  useExtendAttendanceGrace: vi.fn(),
}));

const mutateAsync = vi.fn();

const row = {
  userId: 'u1',
  fullName: 'Ada Lovelace',
  deadline: new Date(2027, 2, 1),
} as MemberAttendanceRow;

beforeEach(() => {
  mutateAsync.mockReset().mockResolvedValue(undefined);
  vi.mocked(useExtendAttendanceGrace).mockReturnValue({
    mutateAsync,
    isPending: false,
  } as unknown as ReturnType<typeof useExtendAttendanceGrace>);
});

describe('ExtendGraceButton', () => {
  it('opens a dialog prefilled with the current deadline and saves it', async () => {
    const user = userEvent.setup();
    render(<ExtendGraceButton row={row} />);

    await user.click(screen.getByRole('button', { name: 'extend grace' }));

    expect(
      screen.getByRole('dialog', { name: 'extend grace for ada lovelace' }),
    ).toBeInTheDocument();
    expect(screen.getByText('monday, march 1, 2027')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'save' }));
    expect(mutateAsync).toHaveBeenCalledWith('2027-03-01');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
