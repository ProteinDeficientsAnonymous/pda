import { type TentativeApprovalMessage, useUpdateTentativeApprovalMessage } from '@/api/content';

import { TemplateEditorDialog } from './TemplateEditorDialog';

interface Props {
  open: boolean;
  onClose: () => void;
  template: TentativeApprovalMessage | null;
}

export function TentativeApprovalMessageEditorDialog({ open, onClose, template }: Props) {
  return (
    <TemplateEditorDialog
      open={open}
      onClose={onClose}
      title="edit tentative approval message"
      description="sent when someone is tentatively approved — this replaces the default message text."
      placeholders={[
        { name: 'FIRST_NAME', hint: "recipient's first name" },
        { name: 'SENDER_NAME' },
        { name: 'MAGIC_LINK', hint: 'their one-time sign in link' },
        { name: 'WHATSAPP_LINK' },
        {
          name: 'NEXT_OFFICIAL_EVENT',
          hint: '"here\'s the next official event:" plus the event; blank if none',
        },
        {
          name: 'CLUB_EVENT',
          hint: 'a club event they picked on the join form, 7+ days out; blank if none',
        },
      ]}
      ariaLabel="tentative approval message body"
      template={template}
      useUpdate={useUpdateTentativeApprovalMessage}
    />
  );
}
