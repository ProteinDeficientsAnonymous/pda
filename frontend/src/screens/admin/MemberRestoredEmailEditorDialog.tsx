import { type MemberRestoredEmail, useUpdateMemberRestoredEmail } from '@/api/memberRestoredEmail';

import { TemplateEditorDialog } from './TemplateEditorDialog';

interface Props {
  open: boolean;
  onClose: () => void;
  template: MemberRestoredEmail | null;
}

export function MemberRestoredEmailEditorDialog({ open, onClose, template }: Props) {
  return (
    <TemplateEditorDialog
      open={open}
      onClose={onClose}
      title="edit welcome back email"
      description="sent automatically when a check-in brings an attendance-paused member back to full membership. links in the body are turned into clickable links."
      placeholders={[
        { name: 'FIRST_NAME', hint: "recipient's first name" },
        { name: 'WHATSAPP_LINK' },
      ]}
      ariaLabel="welcome back email body"
      template={template}
      useUpdate={useUpdateMemberRestoredEmail}
      noun="email"
    />
  );
}
