interface Props {
  href: string;
  label: string;
  disabled?: boolean;
  onClick?: () => void;
}

const CLASS_NAME =
  'focus-visible:ring-brand-200 bg-surface text-foreground border-border-strong hover:bg-background inline-flex h-10 items-center justify-center rounded-md border px-4 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none';

export function SendLink({ href, label, disabled = false, onClick }: Props) {
  if (disabled) {
    return (
      <span aria-disabled="true" className={`${CLASS_NAME} cursor-not-allowed opacity-50`}>
        {label}
      </span>
    );
  }
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      onClick={onClick}
      className={CLASS_NAME}
    >
      {label}
    </a>
  );
}
