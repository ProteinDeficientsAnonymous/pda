import { buttonClass } from './buttonClass';

interface Props {
  href: string;
  label: string;
  disabled?: boolean;
  onClick?: () => void;
}

const CLASS_NAME = buttonClass('secondary');

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
