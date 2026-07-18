import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';

interface Props {
  open: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
  destructive: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  cancelLabel,
  destructive,
  onCancel,
  onConfirm,
}: Props) {
  return (
    <Dialog open={open} onClose={onCancel} title={title}>
      <p className="text-foreground-secondary text-sm whitespace-pre-wrap">{message}</p>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onCancel}>
          {cancelLabel}
        </Button>
        <Button
          variant={destructive ? 'secondary' : 'primary'}
          onClick={onConfirm}
          className={destructive ? 'text-destructive border-destructive' : undefined}
        >
          {confirmLabel}
        </Button>
      </div>
    </Dialog>
  );
}
