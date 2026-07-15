import { useState } from 'react';

import { useTentativeApprovalMessage, useWelcomeTemplate, useWhatsAppLink } from '@/api/content';
import { useAuthStore } from '@/auth/store';
import { hasPermission, Permission } from '@/models/permissions';

import { TentativeApprovalMessageEditorDialog } from './TentativeApprovalMessageEditorDialog';
import { WelcomeTemplateEditorDialog } from './WelcomeTemplateEditorDialog';
import { WhatsAppLinkEditorDialog } from './WhatsAppLinkEditorDialog';

export function JoinRequestMessageEditors() {
  const [welcomeOpen, setWelcomeOpen] = useState(false);
  const [tentativeOpen, setTentativeOpen] = useState(false);
  const [whatsappOpen, setWhatsappOpen] = useState(false);
  const currentUser = useAuthStore((s) => s.user);
  const welcomeQ = useWelcomeTemplate();
  const tentativeQ = useTentativeApprovalMessage();
  const whatsappQ = useWhatsAppLink();

  if (!hasPermission(currentUser, Permission.ApproveJoinRequests)) return null;

  return (
    <div className="mb-4 flex flex-wrap gap-x-4 gap-y-1">
      <button
        type="button"
        onClick={() => {
          setWelcomeOpen(true);
        }}
        className="text-muted hover:text-foreground text-xs underline"
      >
        edit shared welcome template
      </button>
      <button
        type="button"
        onClick={() => {
          setTentativeOpen(true);
        }}
        className="text-muted hover:text-foreground text-xs underline"
      >
        edit tentative approval message
      </button>
      <button
        type="button"
        onClick={() => {
          setWhatsappOpen(true);
        }}
        className="text-muted hover:text-foreground text-xs underline"
      >
        edit whatsapp link
      </button>
      <WelcomeTemplateEditorDialog
        open={welcomeOpen}
        onClose={() => {
          setWelcomeOpen(false);
        }}
        template={welcomeQ.data ?? null}
      />
      <TentativeApprovalMessageEditorDialog
        open={tentativeOpen}
        onClose={() => {
          setTentativeOpen(false);
        }}
        template={tentativeQ.data ?? null}
      />
      <WhatsAppLinkEditorDialog
        open={whatsappOpen}
        onClose={() => {
          setWhatsappOpen(false);
        }}
        whatsappLink={whatsappQ.data ?? null}
      />
    </div>
  );
}
