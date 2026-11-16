import { toast } from 'sonner';

import { useSendProposals } from '@/api/planning';
import { Button } from '@/components/ui/Button';

import { toastOnError } from './toastOnError';

const plural = (n: number, word: string) => `${String(n)} ${word}${n === 1 ? '' : 's'}`;

export function SendProposalsBar({ year, drafts }: { year: number; drafts: number }) {
  const send = useSendProposals(year);
  if (drafts === 0) return null;

  async function sendAll() {
    const sending = send.mutateAsync();
    if (await toastOnError(sending, "couldn't send proposals — try again")) {
      const { planners_notified } = await sending;
      toast.success(`sent to ${plural(planners_notified, 'planner')} 🌱`);
    }
  }

  return (
    <div className="mb-3 flex flex-wrap items-center gap-3">
      <Button disabled={send.isPending} onClick={() => void sendAll()}>
        {`send ${plural(drafts, 'proposal')}`}
      </Button>
      <p className="text-muted text-sm">drafts aren&apos;t sent until you hit send</p>
    </div>
  );
}
