// Shown after approving a join request that created a new user. The magic
// link token is single-use and only returned on that one response — if the
// admin closes this dialog without copying it, they'll need to generate a
// new link from the members screen.

import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { buildMagicLinkUrl, buildSmsHref, buildWelcomeMessage } from '@/utils/welcomeMessage';

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
  const [copied, setCopied] = useState(false);

  if (!magicLinkToken) return null;
  const magicLinkUrl = buildMagicLinkUrl(magicLinkToken);
  const welcomeMessage = buildWelcomeMessage(displayName, magicLinkUrl);
  const smsHref = buildSmsHref(phoneNumber, welcomeMessage);

  async function copyLink() {
    await navigator.clipboard.writeText(magicLinkUrl);
    setCopied(true);
    window.setTimeout(() => {
      setCopied(false);
    }, 2000);
  }

  return (
    <Dialog open={open} onClose={onClose} title={`welcome ${displayName}`}>
      <p className="text-foreground-secondary text-sm">
        share this one-time login link with {phoneNumber}. it won't be shown again.
      </p>
      <div className="bg-surface-dim mt-3 overflow-x-auto rounded-md px-3 py-2 font-mono text-xs break-all">
        {magicLinkUrl}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => void copyLink()}>
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
