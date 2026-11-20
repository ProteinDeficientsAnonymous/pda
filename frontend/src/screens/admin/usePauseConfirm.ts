import { useState } from 'react';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import {
  fetchAttendancePausePreview,
  fetchGuidelinesPausePreview,
  type PauseImpactEvent,
  type PauseOutcome,
  type PausePreview,
  type PauseRole,
} from '@/api/attendancePausePreview';
import { useConfirm } from '@/components/ui/useConfirm';
import { formatShortDateTime } from '@/utils/datetime';

const ROLE_LABEL: Record<PauseRole, string> = {
  rsvp: "rsvp'd",
  hosting: 'hosting',
  cohost_invite: 'co-host invite',
};
const OUTCOME_LABEL: Record<PauseOutcome, string> = {
  kept: 'kept',
  removed: 'removed',
  drafted: 'moved to draft',
  rescinded: 'rescinded',
};

const PAUSE_DIALOG = {
  guidelinesPaused: {
    fetchPreview: fetchGuidelinesPausePreview,
    title: 'pause for guidelines violation?',
  },
  attendancePaused: { fetchPreview: fetchAttendancePausePreview, title: 'pause for event rqmt?' },
};

export type PauseKind = keyof typeof PAUSE_DIALOG;

/** confirmWhenEmpty(boolean): ask even when the preview lists no changes, for a pause applied on confirm */
export function usePauseConfirm({ confirmWhenEmpty = false } = {}) {
  const [loading, setLoading] = useState(false);
  const { confirm, element } = useConfirm();

  async function confirmPause(memberId: string, kind: PauseKind): Promise<boolean> {
    const { fetchPreview, title } = PAUSE_DIALOG[kind];
    setLoading(true);
    try {
      const lines = describePreview(await fetchPreview(memberId));
      if (lines.length === 0 && !confirmWhenEmpty) return true;
      return await confirm({
        title,
        message:
          lines.length === 0
            ? 'nothing upcoming changes for them'
            : `here's what the pause changes:\n\n${lines.join('\n')}`,
        confirmLabel: 'pause',
        destructive: true,
      });
    } catch (err) {
      toast.error(extractApiErrorOr(err, "couldn't load the pause preview — try again"));
      return false;
    } finally {
      setLoading(false);
    }
  }

  return { confirmPause, loading, element };
}

function describePreview(preview: PausePreview): string[] {
  const lines = preview.events.map(describeImpact);
  if (preview.strippedRoles.length > 0) {
    lines.push(`• roles removed: ${preview.strippedRoles.join(', ').toLowerCase()}`);
  }
  if (preview.clearsWhatsapp) lines.push('• marked as not in the whatsapp group');
  return lines;
}

function describeImpact(e: PauseImpactEvent): string {
  const when = e.startDatetime ? formatShortDateTime(e.startDatetime) : 'date tbd';
  return `• ${e.title.toLowerCase()} (${when}) — ${ROLE_LABEL[e.role]} · ${OUTCOME_LABEL[e.outcome]}`;
}
