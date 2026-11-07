import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { fetchAttendancePausePreview } from '@/api/attendancePausePreview';

import { MemberPauseToggles, type PauseState } from './MemberPauseToggles';

vi.mock('@/api/attendancePausePreview', () => ({ fetchAttendancePausePreview: vi.fn() }));

const preview = vi.mocked(fetchAttendancePausePreview);

function Harness() {
  const [value, setValue] = useState<PauseState>({ isPaused: false, attendancePaused: false });
  return (
    <MemberPauseToggles memberId="m1" value={value} onChange={setValue} targetIsAdmin={false} />
  );
}

const eventRqmtSwitch = () => screen.getByRole('switch', { name: 'event rqmt pause' });

describe('MemberPauseToggles event rqmt preview', () => {
  beforeEach(() => {
    preview.mockReset();
  });

  it('turns on without a dialog when nothing is affected', async () => {
    preview.mockResolvedValue([]);
    render(<Harness />);
    await userEvent.click(eventRqmtSwitch());
    expect(preview).toHaveBeenCalledWith('m1');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(eventRqmtSwitch()).toHaveAttribute('aria-checked', 'true');
  });

  it('lists affected events and turns on after confirming', async () => {
    preview.mockResolvedValue([
      { id: 'e1', title: 'Potluck', startDatetime: null, role: 'hosting', outcome: 'drafted' },
      { id: 'e2', title: 'Club Hike', startDatetime: null, role: 'rsvp', outcome: 'kept' },
    ]);
    render(<Harness />);
    await userEvent.click(eventRqmtSwitch());

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('potluck');
    expect(dialog).toHaveTextContent('hosting · moved to draft');
    expect(dialog).toHaveTextContent("rsvp'd · kept");
    expect(eventRqmtSwitch()).toHaveAttribute('aria-checked', 'false');

    await userEvent.click(screen.getByRole('button', { name: 'pause' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(eventRqmtSwitch()).toHaveAttribute('aria-checked', 'true');
  });

  it('stays off when the dialog is cancelled', async () => {
    preview.mockResolvedValue([
      { id: 'e1', title: 'Potluck', startDatetime: null, role: 'rsvp', outcome: 'removed' },
    ]);
    render(<Harness />);
    await userEvent.click(eventRqmtSwitch());
    await userEvent.click(await screen.findByRole('button', { name: 'cancel' }));
    expect(eventRqmtSwitch()).toHaveAttribute('aria-checked', 'false');
  });
});
