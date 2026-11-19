import { type MemberPromotionEmail, useUpdateMemberPromotionEmail } from '@/api/content';

import { TemplateEditorDialog } from './TemplateEditorDialog';

interface Props {
  open: boolean;
  onClose: () => void;
  template: MemberPromotionEmail | null;
}

export function MemberPromotionEmailEditorDialog({ open, onClose, template }: Props) {
  return (
    <TemplateEditorDialog
      open={open}
      onClose={onClose}
      title="edit member promotion email"
      description="sent automatically when a tentatively-approved applicant becomes a full member — on event check-in or manual promotion. links in the body are turned into clickable links."
      placeholders={[
        { name: 'FIRST_NAME', hint: "recipient's first name" },
        { name: 'WHATSAPP_LINK' },
      ]}
      ariaLabel="member promotion email body"
      template={template}
      useUpdate={useUpdateMemberPromotionEmail}
      noun="email"
    />
  );
}
