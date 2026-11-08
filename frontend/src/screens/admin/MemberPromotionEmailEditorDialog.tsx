import { type SyntheticEvent, useState } from 'react';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import { type MemberPromotionEmail, useUpdateMemberPromotionEmail } from '@/api/content';
import { useUpdateMemberRestoredEmail } from '@/api/memberRestoredEmail';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { cn } from '@/utils/cn';

const MAX_LENGTH = 4000;

const COPY = {
  promotion: {
    title: 'edit member promotion email',
    label: 'member promotion email body',
    description:
      'sent automatically when a tentatively-approved applicant becomes a full member — on event check-in or manual promotion.',
  },
  restored: {
    title: 'edit welcome back email',
    label: 'welcome back email body',
    description:
      'sent automatically when a check-in brings an attendance-paused member back to full membership.',
  },
} as const;

type Variant = keyof typeof COPY;

interface Props {
  open: boolean;
  onClose: () => void;
  template: MemberPromotionEmail | null;
  variant?: Variant;
}

export function MemberPromotionEmailEditorDialog({
  open,
  onClose,
  template,
  variant = 'promotion',
}: Props) {
  if (!open) return null;
  // Inner form is keyed on the template body so each open seeds fresh state
  // without an effect.
  return (
    <Dialog open onClose={onClose} title={COPY[variant].title}>
      <EditorForm
        key={template?.body ?? ''}
        initialBody={template?.body ?? ''}
        onClose={onClose}
        variant={variant}
      />
    </Dialog>
  );
}

interface FormProps {
  initialBody: string;
  onClose: () => void;
  variant: Variant;
}

function EditorForm({ initialBody, onClose, variant }: FormProps) {
  const promotion = useUpdateMemberPromotionEmail();
  const restored = useUpdateMemberRestoredEmail();
  const update = variant === 'restored' ? restored : promotion;
  const [body, setBody] = useState(initialBody);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setFormError(null);
    if (!body.trim()) {
      setFormError('message body is required');
      return;
    }
    try {
      await update.mutateAsync(body);
      toast.success('email saved 🌱');
      onClose();
    } catch (err) {
      setFormError(extractApiErrorOr(err, "couldn't save the email — try again"));
    }
  }

  const overLimit = body.length > MAX_LENGTH;
  const nearLimit = body.length > MAX_LENGTH * 0.9;

  return (
    <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-3">
      <p className="text-foreground-secondary text-sm">
        {COPY[variant].description} links in the body are turned into clickable links.
      </p>
      <p className="text-muted text-xs">
        available placeholders:{' '}
        <code className="bg-surface-dim rounded px-1">{'${FIRST_NAME}'}</code> (recipient's first
        name), <code className="bg-surface-dim rounded px-1">{'${WHATSAPP_LINK}'}</code>
      </p>
      <textarea
        value={body}
        onChange={(e) => {
          setBody(e.target.value);
        }}
        rows={10}
        className="border-border bg-background text-foreground focus-visible:ring-brand-200 w-full rounded-md border p-3 font-mono text-base focus-visible:ring-2 focus-visible:outline-none md:text-sm"
        aria-label={COPY[variant].label}
      />
      <div
        className={cn(
          'text-right text-xs',
          overLimit ? 'text-red-600' : nearLimit ? 'text-warning' : 'text-muted',
        )}
      >
        {body.length} / {MAX_LENGTH}
      </div>
      {formError ? (
        <p role="alert" className="text-sm text-red-600">
          {formError}
        </p>
      ) : null}
      <div className="mt-2 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onClose}>
          cancel
        </Button>
        <Button type="submit" disabled={update.isPending || overLimit}>
          {update.isPending ? 'saving…' : 'save'}
        </Button>
      </div>
    </form>
  );
}
