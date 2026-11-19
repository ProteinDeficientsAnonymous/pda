import { useUpdateWelcomeTemplate, type WelcomeTemplate } from '@/api/content';

import { TemplateEditorDialog } from './TemplateEditorDialog';

interface Props {
  open: boolean;
  onClose: () => void;
  template: WelcomeTemplate | null;
}

export function WelcomeTemplateEditorDialog({ open, onClose, template }: Props) {
  return (
    <TemplateEditorDialog
      open={open}
      onClose={onClose}
      title="edit welcome message"
      description="this text is shared with all vetters. changes apply everywhere."
      placeholders={[
        { name: 'FIRST_NAME', hint: "recipient's first name" },
        { name: 'SENDER_NAME' },
        { name: 'MAGIC_LINK' },
        { name: 'WHATSAPP_LINK' },
      ]}
      ariaLabel="welcome message body"
      template={template}
      useUpdate={useUpdateWelcomeTemplate}
      noun="template"
      rows={14}
    />
  );
}
