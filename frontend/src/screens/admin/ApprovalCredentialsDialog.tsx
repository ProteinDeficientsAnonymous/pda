// Shown after approving a join request that created a new user. The magic
// link token is single-use and only returned on that one response — if the
// admin closes this dialog without copying it, they'll need to generate a
// new link from the members screen.

import { useState } from 'react';
import { useAuthStore } from '@/auth/store';
import { useWelcomeTemplate } from '@/api/content';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { hasPermission, Permission } from '@/models/permissions';
import { formatPhone } from '@/utils/formatPhone';
import {
  buildMagicLinkUrl,
  buildSmsHref,
  buildWhatsAppHref,
  buildWelcomeMessage,
  renderWelcomeMessage,
} from '@/utils/welcomeMessage';
import { WelcomeTemplateEditorDialog } from './WelcomeTemplateEditorDialog';

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
  const [editorOpen, setEditorOpen] = useState(false);
  const currentUser = useAuthStore((s) => s.user);
  const templateQ = useWelcomeTemplate();

  if (!magicLinkToken) return null;
  const magicLinkUrl = buildMagicLinkUrl(magicLinkToken);
  const senderName = currentUser?.displayName ?? '';
  // If the template fetch fails, fall back to the legacy hardcoded body so
  // vetters can still send a message.
  const welcomeMessage = templateQ.data
    ? renderWelcomeMessage(templateQ.data.body, {
        name: displayName,
        senderName,
        magicLink: magicLinkUrl,
      })
    : buildWelcomeMessage(displayName, magicLinkUrl);
  const smsHref = buildSmsHref(phoneNumber, welcomeMessage);
  const whatsappHref = buildWhatsAppHref(phoneNumber, welcomeMessage);
  const sendButtonsDisabled = templateQ.isPending;
  const canEditTemplate = hasPermission(currentUser, Permission.EditWelcomeMessage);

  async function copyLink() {
    await navigator.clipboard.writeText(magicLinkUrl);
    setCopied(true);
    window.setTimeout(() => {
      setCopied(false);
    }, 2000);
  }

  return (
    <>
      <Dialog open={open} onClose={onClose} title={`welcome ${displayName}`}>
        <p className="text-foreground-secondary text-sm">
          share this one-time login link with {formatPhone(phoneNumber)}. it won't be shown again.
        </p>
        <div className="bg-surface-dim mt-3 overflow-x-auto rounded-md px-3 py-2 font-mono text-xs break-all">
          {magicLinkUrl}
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => void copyLink()}>
            {copied ? 'copied ✓' : 'copy link'}
          </Button>
          <SendLink href={smsHref} label="send via sms" disabled={sendButtonsDisabled} />
          <SendLink href={whatsappHref} label="send via whatsapp" disabled={sendButtonsDisabled} />
        </div>
        {canEditTemplate ? (
          <div className="mt-3">
            <button
              type="button"
              onClick={() => {
                setEditorOpen(true);
              }}
              className="text-muted hover:text-foreground text-xs underline"
            >
              edit shared welcome template
            </button>
          </div>
        ) : null}
        <div className="mt-4 flex justify-end">
          <Button onClick={onClose}>done</Button>
        </div>
      </Dialog>
      <WelcomeTemplateEditorDialog
        open={editorOpen}
        onClose={() => {
          setEditorOpen(false);
        }}
        template={templateQ.data ?? null}
      />
    </>
  );
}

function SendLink({ href, label, disabled }: { href: string; label: string; disabled: boolean }) {
  const className =
    'focus-visible:ring-brand-200 bg-surface text-foreground border-border-strong hover:bg-background inline-flex h-10 items-center justify-center rounded-md border px-4 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none';
  if (disabled) {
    return (
      <span aria-disabled="true" className={`${className} cursor-not-allowed opacity-50`}>
        {label}
      </span>
    );
  }
  return (
    <a href={href} className={className}>
      {label}
    </a>
  );
}
