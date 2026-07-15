import { useState } from 'react';

import {
  useMembershipPromotionMessage,
  useTentativeApprovalMessage,
  useWelcomeTemplate,
  useWhatsAppLink,
} from '@/api/content';
import { useAuthStore } from '@/auth/store';
import { hasPermission, Permission } from '@/models/permissions';

import { MembershipPromotionMessageEditorDialog } from './MembershipPromotionMessageEditorDialog';
import { TentativeApprovalMessageEditorDialog } from './TentativeApprovalMessageEditorDialog';
import { WelcomeTemplateEditorDialog } from './WelcomeTemplateEditorDialog';
import { WhatsAppLinkEditorDialog } from './WhatsAppLinkEditorDialog';

export function JoinRequestMessageEditors() {
  const [welcomeOpen, setWelcomeOpen] = useState(false);
  const [tentativeOpen, setTentativeOpen] = useState(false);
  const [membershipOpen, setMembershipOpen] = useState(false);
  const [whatsappOpen, setWhatsappOpen] = useState(false);
  const currentUser = useAuthStore((s) => s.user);
  const welcomeQ = useWelcomeTemplate();
  const tentativeQ = useTentativeApprovalMessage();
  const membershipQ = useMembershipPromotionMessage();
  const whatsappQ = useWhatsAppLink();

  if (!hasPermission(currentUser, Permission.ApproveJoinRequests)) return null;

  return (
    <div className="border-border bg-surface-dim mb-4 rounded-md border p-3">
      <p className="text-muted mb-2 text-xs font-medium tracking-wide uppercase">
        message templates
      </p>
      <div className="flex flex-wrap gap-2">
        <EditorTrigger
          label="edit shared welcome template"
          onClick={() => {
            setWelcomeOpen(true);
          }}
        />
        <EditorTrigger
          label="edit tentative approval message"
          onClick={() => {
            setTentativeOpen(true);
          }}
        />
        <EditorTrigger
          label="edit membership promotion message"
          onClick={() => {
            setMembershipOpen(true);
          }}
        />
        <EditorTrigger
          label="edit whatsapp link"
          onClick={() => {
            setWhatsappOpen(true);
          }}
        />
      </div>
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
      <MembershipPromotionMessageEditorDialog
        open={membershipOpen}
        onClose={() => {
          setMembershipOpen(false);
        }}
        template={membershipQ.data ?? null}
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

function EditorTrigger({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="border-border-strong bg-surface text-foreground-secondary hover:bg-background focus-visible:ring-brand-200 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors focus-visible:outline-none"
    >
      {label}
    </button>
  );
}
