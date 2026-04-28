// Dialog for creating a new member from /members. On success, swaps to the
// same welcome-credentials view used after approving a join request so the
// admin can copy the magic-login link before leaving the dialog.

import { useState, type SyntheticEvent } from 'react';
import { extractApiErrorOr } from '@/api/apiErrors';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { TextField } from '@/components/ui/TextField';
import { useCreateUser, type CreateUserResult } from '@/api/users';
import { formatPhone } from '@/utils/formatPhone';
import { buildMagicLinkUrl, buildSmsHref, buildWelcomeMessage } from '@/utils/welcomeMessage';

interface Props {
  open: boolean;
  onClose: () => void;
}

export function MemberCreateDialog({ open, onClose }: Props) {
  const createUser = useCreateUser();
  const [phone, setPhone] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [result, setResult] = useState<CreateUserResult | null>(null);
  const [copied, setCopied] = useState(false);

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setFormError(null);
    if (!phone.trim()) {
      setFormError('phone number is required');
      return;
    }
    try {
      const created = await createUser.mutateAsync({ phoneNumber: phone.trim() });
      setResult(created);
    } catch (err) {
      setFormError(extractError(err));
    }
  }

  function handleClose() {
    setPhone('');
    setFormError(null);
    setResult(null);
    setCopied(false);
    onClose();
  }

  if (result) {
    return (
      <CredentialsView
        open={open}
        result={result}
        copied={copied}
        onCopy={setCopied}
        onClose={handleClose}
      />
    );
  }

  return (
    <Dialog open={open} onClose={handleClose} title="add member">
      <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-3">
        <TextField
          label="phone number"
          hint="they'll set their display name and email during onboarding"
          value={phone}
          maxLength={20}
          onChange={(e) => {
            setPhone(e.target.value);
          }}
          required
        />
        {formError ? (
          <p role="alert" className="text-sm text-red-600">
            {formError}
          </p>
        ) : null}
        <div className="mt-2 flex justify-end gap-2">
          <Button variant="ghost" onClick={handleClose} type="button">
            cancel
          </Button>
          <Button type="submit" disabled={createUser.isPending}>
            {createUser.isPending ? 'creating…' : 'create'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

function CredentialsView({
  open,
  result,
  copied,
  onCopy,
  onClose,
}: {
  open: boolean;
  result: CreateUserResult;
  copied: boolean;
  onCopy: (v: boolean) => void;
  onClose: () => void;
}) {
  const magicLinkUrl = buildMagicLinkUrl(result.magicLinkToken);
  const greeting = result.displayName || formatPhone(result.phoneNumber);
  const welcomeMessage = buildWelcomeMessage(result.displayName, magicLinkUrl);
  const smsHref = buildSmsHref(result.phoneNumber, welcomeMessage);

  async function copy() {
    await navigator.clipboard.writeText(magicLinkUrl);
    onCopy(true);
    window.setTimeout(() => {
      onCopy(false);
    }, 2000);
  }

  return (
    <Dialog open={open} onClose={onClose} title={`welcome ${greeting}`}>
      <p className="text-foreground-secondary text-sm">
        share this one-time login link with {formatPhone(result.phoneNumber)}. it won't be shown
        again.
      </p>
      <div className="bg-surface-dim text-foreground mt-3 overflow-x-auto rounded-md px-3 py-2 font-mono text-xs break-all">
        {magicLinkUrl}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => void copy()}>
          {copied ? 'copied ✓' : 'copy link'}
        </Button>
        <a
          href={smsHref}
          className="focus-visible:ring-brand-200 bg-surface text-foreground border-border-strong hover:bg-background inline-flex h-10 items-center justify-center rounded-md border px-4 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none"
        >
          send welcome message
        </a>
      </div>
      <div className="mt-4 flex justify-end">
        <Button onClick={onClose}>done</Button>
      </div>
    </Dialog>
  );
}

function extractError(err: unknown): string {
  return extractApiErrorOr(err, "couldn't create member — try again");
}
