import { useState } from 'react';

import { useMemberPromotionMessage, useWhatsAppLink } from '@/api/content';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { hasPermission, Permission } from '@/models/permissions';
import { formatPhone } from '@/utils/formatPhone';
import {
  buildMagicLinkUrl,
  buildSmsHref,
  buildWelcomeMessage,
  buildWhatsAppHref,
  renderWelcomeMessage,
} from '@/utils/welcomeMessage';

import { MemberPromotionMessageEditorDialog } from './MemberPromotionMessageEditorDialog';

interface Props {
  open: boolean;
  onClose: () => void;
  fullName: string;
  firstName: string;
  phoneNumber: string;
  magicLinkToken: string | null;
}

export function MemberPromotionMessageDialog({
  open,
  onClose,
  fullName,
  firstName,
  phoneNumber,
  magicLinkToken,
}: Props) {
  const [copied, setCopied] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
  const currentUser = useAuthStore((s) => s.user);
  const templateQ = useMemberPromotionMessage();
  const whatsappLinkQ = useWhatsAppLink();

  if (!magicLinkToken) return null;
  const magicLinkUrl = buildMagicLinkUrl(magicLinkToken);
  const senderName = currentUser?.firstName ?? '';
  // If the template fetch fails, fall back to the legacy hardcoded body so
  // vetters can still send a message.
  const message = templateQ.data
    ? renderWelcomeMessage(templateQ.data.body, {
        name: firstName,
        senderName,
        magicLink: magicLinkUrl,
        whatsappLink: whatsappLinkQ.data?.link ?? '',
      })
    : buildWelcomeMessage(firstName, magicLinkUrl);
  const smsHref = buildSmsHref(phoneNumber, message);
  const whatsappHref = buildWhatsAppHref(phoneNumber, message);
  const sendButtonsDisabled = templateQ.isPending;
  const canEditTemplate = hasPermission(currentUser, Permission.ApproveJoinRequests);

  async function copyLink() {
    await navigator.clipboard.writeText(magicLinkUrl);
    setCopied(true);
    window.setTimeout(() => {
      setCopied(false);
    }, 2000);
  }

  return (
    <>
      <Dialog open={open} onClose={onClose} title={`welcome ${fullName}`}>
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
              className="text-muted hover:text-foreground text-left text-xs underline"
            >
              edit member promotion message
            </button>
          </div>
        ) : null}
        <div className="mt-4 flex justify-end">
          <Button onClick={onClose}>done</Button>
        </div>
      </Dialog>
      <MemberPromotionMessageEditorDialog
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
    <a href={href} target="_blank" rel="noopener noreferrer" className={className}>
      {label}
    </a>
  );
}
