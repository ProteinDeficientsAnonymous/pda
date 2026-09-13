import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { formatPhone } from '@/utils/formatPhone';
import { buildSmsHref, buildWhatsAppHref } from '@/utils/welcomeMessage';

interface Props {
  open: boolean;
  onClose: () => void;
  fullName: string;
  phoneNumber: string;
}

export function SendMessageDialog({ open, onClose, fullName, phoneNumber }: Props) {
  return (
    <Dialog open={open} onClose={onClose} title={`message ${fullName.toLowerCase()}`}>
      <p className="text-foreground-secondary text-sm">
        opens an empty draft to {formatPhone(phoneNumber)} — nothing is pre-written.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <SendLink href={buildSmsHref(phoneNumber)} label="send via sms" onClick={onClose} />
        <SendLink
          href={buildWhatsAppHref(phoneNumber)}
          label="send via whatsapp"
          onClick={onClose}
        />
      </div>
      <div className="mt-4 flex justify-end">
        <Button variant="secondary" onClick={onClose}>
          cancel
        </Button>
      </div>
    </Dialog>
  );
}

function SendLink({ href, label, onClick }: { href: string; label: string; onClick: () => void }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      onClick={onClick}
      className="focus-visible:ring-brand-200 bg-surface text-foreground border-border-strong hover:bg-background inline-flex h-10 items-center justify-center rounded-md border px-4 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none"
    >
      {label}
    </a>
  );
}
