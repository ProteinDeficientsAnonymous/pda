import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import { useUpdateUser } from '@/api/users';
import { Toggle } from '@/components/ui/Toggle';

export function JoinRequestWhatsappToggle({
  userId,
  checked,
}: {
  userId: string;
  checked: boolean;
}) {
  const qc = useQueryClient();
  const update = useUpdateUser(userId);

  async function onChange(next: boolean) {
    try {
      await update.mutateAsync({ hasJoinedWhatsapp: next });
      void qc.invalidateQueries({ queryKey: ['join-requests'] });
    } catch (e) {
      toast.error(extractApiErrorOr(e, "couldn't save changes — try again"));
    }
  }

  return (
    <div className="mt-3 max-w-xs">
      <Toggle
        label="joined whatsapp"
        checked={checked}
        onChange={(v) => void onChange(v)}
        disabled={update.isPending}
      />
    </div>
  );
}
