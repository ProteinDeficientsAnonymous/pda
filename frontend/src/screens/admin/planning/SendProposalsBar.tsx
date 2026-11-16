import { toast } from 'sonner';

import type { useSendProposals } from '@/api/planning';
import { Button } from '@/components/ui/Button';

import { toastOnError } from './toastOnError';

const plural = (n: number, word: string) => `${String(n)} ${word}${n === 1 ? '' : 's'}`;

interface SendProposalsBarProps {
  send: ReturnType<typeof useSendProposals>;
  drafts: number;
}

export function SendProposalsBar({ send, drafts }: SendProposalsBarProps) {
  if (drafts === 0) return null;

  async function sendAll() {
    const sending = send.mutateAsync();
    if (await toastOnError(sending, "couldn't send proposals — try again")) {
      const { planners_notified } = await sending;
      toast.success(`sent to ${plural(planners_notified, 'planner')} 🌱`);
    }
  }

  return (
    <div className="bg-brand-600 text-brand-on mb-3 flex flex-wrap items-center justify-between gap-3 rounded-full py-2 pr-2 pl-5">
      <p className="text-sm font-medium">{`${String(drafts)} not sent yet`}</p>
      <Button
        disabled={send.isPending}
        onClick={() => void sendAll()}
        className="text-brand-700 bg-white hover:bg-white/90"
      >
        send proposals
      </Button>
    </div>
  );
}
