import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { toast } from 'sonner';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  fetchAttendancePausePreview,
  fetchGuidelinesPausePreview,
  type PauseImpactEvent,
  type PausePreview,
} from '@/api/attendancePausePreview';

import { MemberPauseToggles, type PauseState } from './MemberPauseToggles';

vi.mock('@/api/attendancePausePreview', () => ({
  fetchAttendancePausePreview: vi.fn(),
  fetchGuidelinesPausePreview: vi.fn(),
}));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const preview = vi.mocked(fetchAttendancePausePreview);
const previewOf = (events: PauseImpactEvent[], extra: Partial<PausePreview> = {}) => ({
  events,
  strippedRoles: [],
  clearsWhatsapp: false,
  ...extra,
});
const guidelinesPreview = vi.mocked(fetchGuidelinesPausePreview);

function Harness({ guidelinesPaused = false, attendancePaused = false }: Partial<PauseState>) {
  const [value, setValue] = useState<PauseState>({ guidelinesPaused, attendancePaused });
  return (
    <MemberPauseToggles memberId="m1" value={value} onChange={setValue} targetIsAdmin={false} />
  );
}

const eventRqmtSwitch = () => screen.getByRole('switch', { name: 'event rqmt pause' });
const guidelinesSwitch = () => screen.getByRole('switch', { name: 'guidelines violation pause' });

describe('MemberPauseToggles event rqmt preview', () => {
  beforeEach(() => {
    preview.mockReset();
  });

  it('turns on without a dialog when nothing is affected', async () => {
    preview.mockResolvedValue(previewOf([]));
    render(<Harness />);
    await userEvent.click(eventRqmtSwitch());
    expect(preview).toHaveBeenCalledWith('m1');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(eventRqmtSwitch()).toHaveAttribute('aria-checked', 'true');
  });

  it('shows a toast and stays off when the preview fails', async () => {
    preview.mockRejectedValue(new Error('network down'));
    render(<Harness />);
    await userEvent.click(eventRqmtSwitch());
    expect(toast.error).toHaveBeenCalledWith("couldn't load their upcoming events — try again");
    expect(eventRqmtSwitch()).toHaveAttribute('aria-checked', 'false');
  });

  it('locks an existing event rqmt pause until they check in', () => {
    render(<Harness attendancePaused />);
    expect(eventRqmtSwitch()).toBeDisabled();
    expect(eventRqmtSwitch()).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByText(/lifts when they check in/)).toBeInTheDocument();
  });

  it('lists affected events and turns on after confirming', async () => {
    preview.mockResolvedValue(
      previewOf([
        { id: 'e1', title: 'Potluck', startDatetime: null, role: 'hosting', outcome: 'drafted' },
        { id: 'e2', title: 'Club Hike', startDatetime: null, role: 'rsvp', outcome: 'kept' },
      ]),
    );
    render(<Harness />);
    await userEvent.click(eventRqmtSwitch());

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('potluck');
    expect(dialog).toHaveTextContent('hosting · moved to draft');
    expect(dialog).toHaveTextContent("rsvp'd · kept");
    expect(eventRqmtSwitch()).toHaveAttribute('aria-checked', 'false');
    expect(screen.getByRole('switch', { name: 'guidelines violation pause' })).toBeDisabled();

    await userEvent.click(screen.getByRole('button', { name: 'pause' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(eventRqmtSwitch()).toHaveAttribute('aria-checked', 'true');
  });

  it('lists invites, roles and the whatsapp flag', async () => {
    preview.mockResolvedValue(
      previewOf(
        [
          {
            id: 'e1',
            title: 'Potluck',
            startDatetime: null,
            role: 'cohost_invite',
            outcome: 'rescinded',
          },
        ],
        { strippedRoles: ['Vetter', 'host'], clearsWhatsapp: true },
      ),
    );
    render(<Harness />);
    await userEvent.click(eventRqmtSwitch());

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('potluck (date tbd) — co-host invite · rescinded');
    expect(dialog).toHaveTextContent('roles removed: vetter, host');
    expect(dialog).toHaveTextContent('marked as not in the whatsapp');
  });

  it('confirms when only roles change', async () => {
    preview.mockResolvedValue(previewOf([], { strippedRoles: ['host'] }));
    render(<Harness />);
    await userEvent.click(eventRqmtSwitch());
    expect(await screen.findByRole('dialog')).toHaveTextContent('roles removed: host');
  });

  it('stays off when the dialog is cancelled', async () => {
    preview.mockResolvedValue(
      previewOf([
        { id: 'e1', title: 'Potluck', startDatetime: null, role: 'rsvp', outcome: 'removed' },
      ]),
    );
    render(<Harness />);
    await userEvent.click(eventRqmtSwitch());
    await userEvent.click(await screen.findByRole('button', { name: 'cancel' }));
    expect(eventRqmtSwitch()).toHaveAttribute('aria-checked', 'false');
  });
});

describe('MemberPauseToggles guidelines preview', () => {
  beforeEach(() => {
    guidelinesPreview.mockReset();
  });

  it('lists affected events and turns on after confirming', async () => {
    guidelinesPreview.mockResolvedValue(
      previewOf([
        { id: 'e1', title: 'Club Hike', startDatetime: null, role: 'rsvp', outcome: 'removed' },
      ]),
    );
    render(<Harness />);
    await userEvent.click(guidelinesSwitch());

    const dialog = await screen.findByRole('dialog');
    expect(guidelinesPreview).toHaveBeenCalledWith('m1');
    expect(dialog).toHaveTextContent('pause for guidelines violation?');
    expect(dialog).toHaveTextContent("club hike (date tbd) — rsvp'd · removed");
    expect(guidelinesSwitch()).toHaveAttribute('aria-checked', 'false');

    await userEvent.click(screen.getByRole('button', { name: 'pause' }));
    expect(guidelinesSwitch()).toHaveAttribute('aria-checked', 'true');
  });

  it('stays off when the dialog is cancelled', async () => {
    guidelinesPreview.mockResolvedValue(
      previewOf([
        { id: 'e1', title: 'Potluck', startDatetime: null, role: 'hosting', outcome: 'drafted' },
      ]),
    );
    render(<Harness />);
    await userEvent.click(guidelinesSwitch());
    await userEvent.click(await screen.findByRole('button', { name: 'cancel' }));
    expect(guidelinesSwitch()).toHaveAttribute('aria-checked', 'false');
  });

  it('lifts an existing pause without a preview and warns it leaves an event rqmt pause', async () => {
    render(<Harness guidelinesPaused />);
    expect(eventRqmtSwitch()).toBeDisabled();
    await userEvent.click(guidelinesSwitch());
    expect(guidelinesPreview).not.toHaveBeenCalled();
    expect(guidelinesSwitch()).toHaveAttribute('aria-checked', 'false');
    expect(screen.getByText(/leaves an event rqmt pause/)).toBeInTheDocument();
  });

  it('drops a pending event rqmt pause and locks that toggle', async () => {
    preview.mockResolvedValue(previewOf([]));
    guidelinesPreview.mockResolvedValue(previewOf([]));
    render(<Harness />);
    await userEvent.click(eventRqmtSwitch());
    expect(eventRqmtSwitch()).toHaveAttribute('aria-checked', 'true');

    await userEvent.click(guidelinesSwitch());

    expect(guidelinesSwitch()).toHaveAttribute('aria-checked', 'true');
    expect(eventRqmtSwitch()).toHaveAttribute('aria-checked', 'false');
    expect(eventRqmtSwitch()).toBeDisabled();
  });
});
