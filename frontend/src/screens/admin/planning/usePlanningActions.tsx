import type { ReactNode } from 'react';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';

import {
  type Assignment,
  type PlannerColumn,
  type PlanningSlot,
  useCommit,
  useConfirmPlanner,
  usePropose,
  useSendProposals,
  useWithdraw,
} from '@/api/planning';
import { useAuthStore } from '@/auth/store';
import { useConfirm } from '@/components/ui/useConfirm';

import { cellActionLabel, type CellState, isWithdrawable } from './gridCell';
import { withTab } from './planningTab';
import { readOnlyTapNotice } from './readOnlyTap';
import { toastOnError } from './toastOnError';

const READ_ONLY_TAP_TOAST = 'planning-read-only-tap';

type Act = (
  slot: PlanningSlot,
  planner: PlannerColumn,
  state: CellState,
  assignment: Assignment | undefined,
) => Promise<void>;

interface PlanningActions {
  act: Act;
  tap: Act;
  readOnlyTap: Act;
  busy: boolean;
  send: ReturnType<typeof useSendProposals>;
  confirmElement: ReactNode;
}

export function usePlanningActions(year: number): PlanningActions {
  const propose = usePropose();
  const withdraw = useWithdraw();
  const confirmPlanner = useConfirmPlanner();
  const commit = useCommit();
  const meId = useAuthStore((s) => s.user?.id);
  const [, setParams] = useSearchParams();
  const send = useSendProposals(year);
  const { confirm, element } = useConfirm();

  async function act(
    slot: PlanningSlot,
    planner: PlannerColumn,
    state: CellState,
    assignment: Assignment | undefined,
  ) {
    if (state === 'draft' && assignment) {
      await toastOnError(
        withdraw.mutateAsync(assignment.id),
        "couldn't remove that draft — try again",
      );
      return;
    }
    if (!isWithdrawable(state)) {
      await toastOnError(
        propose.mutateAsync({ slotId: slot.id, userId: planner.userId }),
        "couldn't propose that slot — try again",
      );
      return;
    }
    const ok = await confirm({
      message: `${cellActionLabel(state, planner.name, slot.label)}?`,
      confirmLabel: 'withdraw',
      destructive: true,
    });
    if (ok && assignment) {
      await toastOnError(
        withdraw.mutateAsync(assignment.id),
        "couldn't withdraw that slot — try again",
      );
    }
  }

  async function tap(...args: Parameters<Act>) {
    const [slot, planner, state] = args;
    const self = planner.userId === meId;
    if (state === 'declined') {
      const ok = await confirm(
        self
          ? { message: `put yourself in for ${slot.label}? you said no`, confirmLabel: 'put me in' }
          : {
              message: `propose ${planner.name} for ${slot.label} again? they said no`,
              confirmLabel: 'propose again',
            },
      );
      if (!ok) return;
    }
    if (!self || state === 'committed') {
      await act(...args);
      return;
    }
    await toastOnError(
      confirmPlanner.mutateAsync({ slotId: slot.id, userId: planner.userId }),
      "couldn't put you in — try again",
    );
  }

  function openAvailability() {
    setParams((prev) => withTab(prev, 'availability'), { replace: true });
  }

  async function readOnlyTap(...[slot, planner, state, assignment]: Parameters<Act>) {
    const self = planner.userId === meId;
    const notice = readOnlyTapNotice(state, self, planner.submitted, slot.label);
    if (notice) {
      toast(notice.message, {
        id: READ_ONLY_TAP_TOAST,
        ...(notice.toAvailability && {
          action: { label: 'my availability', onClick: openAvailability },
        }),
      });
      return;
    }
    if (!assignment) return;
    await toastOnError(commit.mutateAsync(assignment.id), "couldn't put you in — try again");
  }

  return {
    act,
    tap,
    readOnlyTap,
    busy:
      propose.isPending ||
      withdraw.isPending ||
      confirmPlanner.isPending ||
      commit.isPending ||
      send.isPending,
    send,
    confirmElement: element,
  };
}
