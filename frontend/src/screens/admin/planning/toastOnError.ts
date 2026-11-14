import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';

export async function toastOnError(action: Promise<unknown>, fallback: string): Promise<boolean> {
  try {
    await action;
    return true;
  } catch (err) {
    toast.error(extractApiErrorOr(err, fallback));
    return false;
  }
}
