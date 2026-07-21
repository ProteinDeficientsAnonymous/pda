import { useState } from 'react';

import {
  useMemberPromotionMessage,
  useTentativeApprovalMessage,
  useWelcomeTemplate,
  useWhatsAppLink,
} from '@/api/content';
import { useAuthStore } from '@/auth/store';
import { hasPermission, Permission } from '@/models/permissions';

import { MemberPromotionMessageEditorDialog } from './MemberPromotionMessageEditorDialog';
import { TentativeApprovalMessageEditorDialog } from './TentativeApprovalMessageEditorDialog';
import { WelcomeTemplateEditorDialog } from './WelcomeTemplateEditorDialog';
import { WhatsAppLinkEditorDialog } from './WhatsAppLinkEditorDialog';

type EditorKey = 'welcome' | 'tentative' | 'memberPromotion' | 'whatsapp';

const EDITOR_OPTIONS: { value: EditorKey; label: string }[] = [
  { value: 'welcome', label: 'edit shared welcome template' },
  { value: 'tentative', label: 'edit tentative approval message' },
  { value: 'memberPromotion', label: 'edit member promotion message' },
  { value: 'whatsapp', label: 'edit whatsapp link' },
];

export function JoinRequestMessageEditors() {
  const [openEditor, setOpenEditor] = useState<EditorKey | null>(null);
  const currentUser = useAuthStore((s) => s.user);
  const welcomeQ = useWelcomeTemplate();
  const tentativeQ = useTentativeApprovalMessage();
  const memberPromotionQ = useMemberPromotionMessage();
  const whatsappQ = useWhatsAppLink();

  if (!hasPermission(currentUser, Permission.ApproveJoinRequests)) return null;

  function closeEditor() {
    setOpenEditor(null);
  }

  return (
    <div className="border-border bg-surface-dim mb-4 rounded-md border p-3">
      <label
        htmlFor="join-request-message-template-select"
        className="text-muted mb-2 block text-xs font-medium tracking-wide uppercase"
      >
        message templates
      </label>
      <select
        id="join-request-message-template-select"
        className="border-border-strong bg-surface text-foreground-secondary focus-visible:ring-brand-200 w-full rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none"
        value=""
        onChange={(e) => {
          setOpenEditor(e.target.value as EditorKey);
        }}
      >
        <option value="" disabled>
          choose a template to edit&hellip;
        </option>
        {EDITOR_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <WelcomeTemplateEditorDialog
        open={openEditor === 'welcome'}
        onClose={closeEditor}
        template={welcomeQ.data ?? null}
      />
      <TentativeApprovalMessageEditorDialog
        open={openEditor === 'tentative'}
        onClose={closeEditor}
        template={tentativeQ.data ?? null}
      />
      <MemberPromotionMessageEditorDialog
        open={openEditor === 'memberPromotion'}
        onClose={closeEditor}
        template={memberPromotionQ.data ?? null}
      />
      <WhatsAppLinkEditorDialog
        open={openEditor === 'whatsapp'}
        onClose={closeEditor}
        whatsappLink={whatsappQ.data ?? null}
      />
    </div>
  );
}
