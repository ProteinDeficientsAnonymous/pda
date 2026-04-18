// Shown after approving a join request that created a new user. The magic
// link token is single-use and only returned on that one response — if the
// admin closes this dialog without copying it, they'll need to generate a
// new link from the members screen.

import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';

interface Props {
  open: boolean;
  onClose: () => void;
  displayName: string;
  phoneNumber: string;
  magicLinkToken: string | null;
}

export function ApprovalCredentialsDialog({
  open,
  onClose,
  displayName,
  phoneNumber,
  magicLinkToken,
}: Props) {
  const [copied, setCopied] = useState<'none' | 'link' | 'all'>('none');

  if (!magicLinkToken) return null;
  const magicLinkUrl = `${window.location.origin}/magic-login/${magicLinkToken}`;
  const shareText = `hi ${displayName} 🌱 welcome to pda! use this link to sign in: ${magicLinkUrl}`;

  async function copy(value: string, kind: 'link' | 'all') {
    await navigator.clipboard.writeText(value);
    setCopied(kind);
    window.setTimeout(() => {
      setCopied('none');
    }, 2000);
  }

  return (
    <Dialog open={open} onClose={onClose} title={`welcome ${displayName}`}>
      <p className="text-sm text-neutral-700">
        share this one-time login link with {phoneNumber}. it won't be shown again.
      </p>
      <div className="mt-3 overflow-x-auto rounded-md bg-neutral-100 px-3 py-2 font-mono text-xs break-all">
        {magicLinkUrl}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => void copy(magicLinkUrl, 'link')}>
          {copied === 'link' ? 'copied ✓' : 'copy link'}
        </Button>
        <Button variant="secondary" onClick={() => void copy(shareText, 'all')}>
          {copied === 'all' ? 'copied ✓' : 'copy share message'}
        </Button>
      </div>
      <div className="mt-4 flex justify-end">
        <Button onClick={onClose}>done</Button>
      </div>
    </Dialog>
  );
}
