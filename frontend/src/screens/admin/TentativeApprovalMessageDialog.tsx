import { useState } from 'react';

import { useTentativeApprovalMessage, useWhatsAppLink } from '@/api/content';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { hasPermission, Permission } from '@/models/permissions';
import { formatPhone } from '@/utils/formatPhone';
import {
  buildRsvpLinkUrl,
  buildSmsHref,
  buildWhatsAppHref,
  renderWelcomeMessage,
} from '@/utils/welcomeMessage';

import { TentativeApprovalMessageEditorDialog } from './TentativeApprovalMessageEditorDialog';

interface Props {
  open: boolean;
  onClose: () => void;
  fullName: string;
  firstName: string;
  phoneNumber: string;
  rsvpLinkToken: string | null;
}

const DEFAULT_TENTATIVE_MESSAGE =
  "hi ${FIRST_NAME} 🌱 you're tentatively in! come to an event in person and we'll get you fully approved.";

export function TentativeApprovalMessageDialog({
  open,
  onClose,
  fullName,
  firstName,
  phoneNumber,
  rsvpLinkToken,
}: Props) {
  const [editorOpen, setEditorOpen] = useState(false);
  const currentUser = useAuthStore((s) => s.user);
  const templateQ = useTentativeApprovalMessage();
  const whatsappLinkQ = useWhatsAppLink();

  const senderName = currentUser?.firstName ?? '';
  const body = templateQ.data?.body.trim() ? templateQ.data.body : DEFAULT_TENTATIVE_MESSAGE;
  const message = renderWelcomeMessage(body, {
    name: firstName,
    senderName,
    rsvpLink: rsvpLinkToken ? buildRsvpLinkUrl(rsvpLinkToken) : '',
    whatsappLink: whatsappLinkQ.data?.link ?? '',
  });
  const smsHref = buildSmsHref(phoneNumber, message);
  const whatsappHref = buildWhatsAppHref(phoneNumber, message);
  const sendButtonsDisabled = templateQ.isPending;
  const canEditTemplate = hasPermission(currentUser, Permission.ApproveJoinRequests);

  return (
    <>
      <Dialog open={open} onClose={onClose} title={`welcome ${fullName}`}>
        <p className="text-foreground-secondary text-sm">
          let {formatPhone(phoneNumber)} know they're tentatively in.
        </p>
        <div className="bg-surface-dim mt-3 overflow-x-auto rounded-md px-3 py-2 text-xs break-words whitespace-pre-wrap">
          {message}
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
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
              edit tentative approval message
            </button>
          </div>
        ) : null}
        <div className="mt-4 flex justify-end">
          <Button onClick={onClose}>done</Button>
        </div>
      </Dialog>
      <TentativeApprovalMessageEditorDialog
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
