import type { ReactNode } from 'react';

import {
  type Assignment,
  type PlannerColumn,
  type PlanningSlot,
  usePropose,
  useSendProposals,
  useWithdraw,
} from '@/api/planning';
import { useConfirm } from '@/components/ui/useConfirm';

import { type CellState, isWithdrawable } from './gridCell';
import { toastOnError } from './toastOnError';

interface PlanningActions {
  act: (
    slot: PlanningSlot,
    planner: PlannerColumn,
    state: CellState,
    assignment: Assignment | undefined,
  ) => Promise<void>;
  busy: boolean;
  send: ReturnType<typeof useSendProposals>;
  confirmElement: ReactNode;
}

export function usePlanningActions(year: number): PlanningActions {
  const propose = usePropose();
  const withdraw = useWithdraw();
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
      message: `withdraw ${planner.name} from ${slot.label}?`,
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

  return {
    act,
    busy: propose.isPending || withdraw.isPending || send.isPending,
    send,
    confirmElement: element,
  };
}
