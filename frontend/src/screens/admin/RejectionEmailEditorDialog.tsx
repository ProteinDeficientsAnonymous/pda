import { type SyntheticEvent, useState } from 'react';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import {
  PRESET_REJECTION_REASONS,
  type PresetRejectionReason,
  REJECTION_REASON_LABELS,
  type RejectionEmail,
  useUpdateRejectionEmail,
} from '@/api/rejectionEmail';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Textarea } from '@/components/ui/Textarea';

const BODY_MAX_LENGTH = 4000;
const REASON_MAX_LENGTH = 1000;

interface Props {
  open: boolean;
  onClose: () => void;
  template: RejectionEmail | null;
}

export function RejectionEmailEditorDialog({ open, onClose, template }: Props) {
  if (!open || !template) return null;
  // Keyed on updatedAt so each open seeds fresh state without an effect.
  return (
    <Dialog open onClose={onClose} title="edit rejection email" wide>
      <EditorForm key={template.updatedAt} template={template} onClose={onClose} />
    </Dialog>
  );
}

function EditorForm({ template, onClose }: { template: RejectionEmail; onClose: () => void }) {
  const update = useUpdateRejectionEmail();
  const [body, setBody] = useState(template.body);
  const [reasons, setReasons] = useState(template.reasons);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setFormError(null);
    if (!body.trim()) {
      setFormError('email body is required');
      return;
    }
    if (PRESET_REJECTION_REASONS.some((key) => !reasons[key].trim())) {
      setFormError('each reason needs email text');
      return;
    }
    try {
      await update.mutateAsync({ body, reasons });
      toast.success('email saved 🌱');
      onClose();
    } catch (err) {
      setFormError(extractApiErrorOr(err, "couldn't save the email — try again"));
    }
  }

  function setReason(key: PresetRejectionReason, text: string) {
    setReasons((prev) => ({ ...prev, [key]: text }));
  }

  return (
    <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-3">
      <p className="text-foreground-secondary text-sm">
        sent automatically when a join request is rejected — links in the body are turned into
        clickable links
      </p>
      <p className="text-muted text-xs">
        available placeholders:{' '}
        <code className="bg-surface-dim rounded px-1">{'${FIRST_NAME}'}</code> (recipient's first
        name), <code className="bg-surface-dim rounded px-1">{'${REASON}'}</code> (the reason text
        below, or what the vetter wrote for "other" — blank if no reason was picked)
      </p>
      <Textarea
        label="email body"
        rows={8}
        value={body}
        maxLength={BODY_MAX_LENGTH}
        className="font-mono"
        onChange={(e) => {
          setBody(e.target.value);
        }}
      />
      {PRESET_REJECTION_REASONS.map((key) => (
        <Textarea
          key={key}
          label={REJECTION_REASON_LABELS[key]}
          rows={3}
          value={reasons[key]}
          maxLength={REASON_MAX_LENGTH}
          onChange={(e) => {
            setReason(key, e.target.value);
          }}
        />
      ))}
      {formError ? (
        <p role="alert" className="text-sm text-red-600">
          {formError}
        </p>
      ) : null}
      <div className="mt-2 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onClose}>
          cancel
        </Button>
        <Button type="submit" disabled={update.isPending}>
          {update.isPending ? 'saving…' : 'save'}
        </Button>
      </div>
    </form>
  );
}
