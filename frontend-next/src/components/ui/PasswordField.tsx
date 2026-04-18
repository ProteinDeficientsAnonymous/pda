import { forwardRef, useState, type InputHTMLAttributes } from 'react';
import { TextField } from './TextField';

type BaseProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'>;

interface Props extends BaseProps {
  label: string;
  error?: string | undefined;
  hint?: string | undefined;
}

export const PasswordField = forwardRef<HTMLInputElement, Props>(function PasswordField(
  { label, error, hint, ...rest },
  ref,
) {
  const [visible, setVisible] = useState(false);
  return (
    <TextField
      {...rest}
      ref={ref}
      label={label}
      error={error}
      hint={hint}
      type={visible ? 'text' : 'password'}
      rightAdornment={
        <button
          type="button"
          onClick={() => {
            setVisible((v) => !v);
          }}
          aria-label={visible ? 'hide password' : 'show password'}
          aria-pressed={visible}
          className="flex h-8 w-8 items-center justify-center rounded-md text-neutral-500 hover:text-neutral-800 focus:text-neutral-800 focus:ring-2 focus:ring-neutral-300 focus:outline-none"
        >
          {visible ? <EyeOffIcon /> : <EyeIcon />}
        </button>
      }
    />
  );
});

function EyeIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M17.94 17.94A10.94 10.94 0 0 1 12 19c-7 0-10-7-10-7a19.77 19.77 0 0 1 4.22-5.06" />
      <path d="M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 10 7 10 7a19.8 19.8 0 0 1-3.16 4.19" />
      <path d="M14.12 14.12A3 3 0 1 1 9.88 9.88" />
      <line x1="2" y1="2" x2="22" y2="22" />
    </svg>
  );
}
