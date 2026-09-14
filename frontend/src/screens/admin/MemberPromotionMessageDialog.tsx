import { useState } from 'react';

import { useMemberPromotionMessage, useWhatsAppLink } from '@/api/content';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { SendLink } from '@/components/ui/SendLink';
import { hasPermission, Permission } from '@/models/permissions';
import { formatPhone } from '@/utils/formatPhone';
import { buildSmsHref, buildWhatsAppHref, renderWelcomeMessage } from '@/utils/welcomeMessage';

import { MemberPromotionMessageEditorDialog } from './MemberPromotionMessageEditorDialog';

interface Props {
  open: boolean;
  onClose: () => void;
  fullName: string;
  // Sourced from join-request rows, where either can be absent.
  firstName: string | null | undefined;
  phoneNumber: string | null | undefined;
}

function fallbackMessage(name: string): string {
  return `${name ? `hi ${name} 🌱` : 'hi 🌱'} you're a full member now — welcome in!`;
}

export function MemberPromotionMessageDialog({
  open,
  onClose,
  fullName,
  firstName,
  phoneNumber,
}: Props) {
  const [editorOpen, setEditorOpen] = useState(false);
  const currentUser = useAuthStore((s) => s.user);
  const templateQ = useMemberPromotionMessage();
  const whatsappLinkQ = useWhatsAppLink();

  const senderName = currentUser?.firstName ?? '';
  const name = (firstName ?? '').trim();
  const phone = phoneNumber ?? '';
  // If the template fetch fails, fall back to a plain body so vetters can
  // still send something.
  const message = templateQ.data
    ? renderWelcomeMessage(templateQ.data.body, {
        name,
        senderName,
        whatsappLink: whatsappLinkQ.data?.link ?? '',
      })
    : fallbackMessage(name);
  const smsHref = buildSmsHref(phone, message);
  const whatsappHref = buildWhatsAppHref(phone, message);
  const sendButtonsDisabled = templateQ.isPending;
  const canEditTemplate = hasPermission(currentUser, Permission.ApproveJoinRequests);

  return (
    <>
      <Dialog open={open} onClose={onClose} title={`welcome ${fullName}`}>
        <p className="text-foreground-secondary text-sm">
          let {formatPhone(phone)} know they're a full member now — they sign in the same way they
          already do.
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
