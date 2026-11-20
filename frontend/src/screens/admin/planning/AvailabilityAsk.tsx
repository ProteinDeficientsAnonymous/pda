import { format } from 'date-fns';
import { toast } from 'sonner';

import { useOpenAvailability, usePlanningYears } from '@/api/planning';
import { Button } from '@/components/ui/Button';
import { useConfirm } from '@/components/ui/useConfirm';
import { parseIsoDate } from '@/utils/datetime';

import { toastOnError } from './toastOnError';

export function AvailabilityAsk({ year }: { year: number }) {
  const years = usePlanningYears();
  const open = useOpenAvailability(year);
  const { confirm, element } = useConfirm();
  const openedAt = years.data?.find((y) => y.year === year)?.availability_opened_at;
  if (openedAt === undefined) return null;

  async function ask() {
    const ok = await confirm({
      title: 'ask planners for availability?',
      message: `this emails every planner asking when they can plan in ${String(year)}, then once a week to anyone who hasn't filled it in — you can only send it once`,
      confirmLabel: 'send',
    });
    if (!ok) return;
    if (await toastOnError(open.mutateAsync(), "couldn't ask planners — try again")) {
      toast.success('planners asked 🌱');
    }
  }

  if (openedAt !== null) {
    const day = format(parseIsoDate(openedAt), 'MMM d').toLowerCase();
    return (
      <p className="text-foreground-secondary text-sm">
        {`✓ planners asked for availability on ${day} — anyone who hasn't filled it in gets a weekly email until ${String(year)} starts`}
      </p>
    );
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-foreground-secondary min-w-60 flex-1 text-sm">
        once the slots look right, ask planners when they can plan
      </p>
      <Button disabled={open.isPending} onClick={() => void ask()}>
        ask planners for availability
      </Button>
      {element}
    </div>
  );
}
