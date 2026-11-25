import { useState } from 'react';

import { useTentativeApprovalMessage, useWhatsAppLink } from '@/api/content';
import { useJoinRequestSuggestedEvents } from '@/api/joinSuggestedEvents';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { SendLink } from '@/components/ui/SendLink';
import { hasPermission, Permission } from '@/models/permissions';
import { formatPhone } from '@/utils/formatPhone';
import {
  buildEventSection,
  buildMagicLinkUrl,
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
  magicLinkToken: string | null;
  joinRequestId: string;
}

const DEFAULT_TENTATIVE_MESSAGE =
  "hi ${FIRST_NAME} 🌱 you're tentatively in! sign in here: ${MAGIC_LINK} — come to an event in person and we'll get you fully approved.\n\n${NEXT_OFFICIAL_EVENT}\n\n${CLUB_EVENT}";

export function TentativeApprovalMessageDialog({
  open,
  onClose,
  fullName,
  firstName,
  phoneNumber,
  magicLinkToken,
  joinRequestId,
}: Props) {
  const [editorOpen, setEditorOpen] = useState(false);
  const currentUser = useAuthStore((s) => s.user);
  const templateQ = useTentativeApprovalMessage();
  const whatsappLinkQ = useWhatsAppLink();
  const eventsQ = useJoinRequestSuggestedEvents(joinRequestId);

  const senderName = currentUser?.firstName ?? '';
  const body = templateQ.data?.body.trim() ? templateQ.data.body : DEFAULT_TENTATIVE_MESSAGE;
  const message = renderWelcomeMessage(body, {
    name: firstName,
    senderName,
    magicLink: magicLinkToken ? buildMagicLinkUrl(magicLinkToken) : '',
    whatsappLink: whatsappLinkQ.data?.link ?? '',
    nextOfficialEvent: buildEventSection(
      "here's the next official event:",
      eventsQ.data?.nextOfficialEvent ?? null,
    ),
    clubEvent: buildEventSection(
      "here's a club event we think you'd love:",
      eventsQ.data?.clubEvent ?? null,
    ),
  });
  const smsHref = buildSmsHref(phoneNumber, message);
  const whatsappHref = buildWhatsAppHref(phoneNumber, message);
  // A failed events fetch just leaves the sections out rather than blocking the send.
  const sendButtonsDisabled = templateQ.isPending || eventsQ.isPending;
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
