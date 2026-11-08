import { type MemberPromotionMessage, useUpdateMemberPromotionMessage } from '@/api/content';

import { TemplateEditorDialog } from './TemplateEditorDialog';

interface Props {
  open: boolean;
  onClose: () => void;
  template: MemberPromotionMessage | null;
}

export function MemberPromotionMessageEditorDialog({ open, onClose, template }: Props) {
  const update = useUpdateMemberPromotionMessage();
  return (
    <TemplateEditorDialog
      open={open}
      onClose={onClose}
      title="edit member promotion message"
      description="sent when a tentatively-approved applicant is manually promoted to full member — this replaces the default message text. they already have a login, so there is no link to share."
      placeholders={[
        { name: 'FIRST_NAME', hint: "recipient's first name" },
        { name: 'SENDER_NAME' },
        { name: 'WHATSAPP_LINK' },
      ]}
      ariaLabel="member promotion message body"
      template={template}
      update={update}
    />
  );
}
