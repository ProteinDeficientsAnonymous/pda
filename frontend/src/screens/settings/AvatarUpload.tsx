import { useRef, useState } from 'react';
import { isAxiosError } from 'axios';
import { ImageCropDialog } from '@/components/ImageCropDialog';
import { useAuthStore } from '@/auth/store';
import { cn } from '@/utils/cn';

const MAX_FILE_BYTES = 5 * 1024 * 1024;
const ALLOWED_MIME = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/gif',
  'image/heic',
  'image/heif',
];

interface Props {
  size?: 'md' | 'lg';
}

export function AvatarUpload({ size = 'md' }: Props) {
  const user = useAuthStore((s) => s.user);
  const upload = useAuthStore((s) => s.uploadProfilePhoto);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!user) return null;
  const initials = user.displayName.slice(0, 2).toLowerCase() || '?';
  const photoUrl = user.profilePhotoUrl
    ? user.photoUpdatedAt
      ? `${user.profilePhotoUrl}?v=${encodeURIComponent(user.photoUpdatedAt)}`
      : user.profilePhotoUrl
    : '';

  const avatarSize = size === 'lg' ? 'h-28 w-28' : 'h-20 w-20';
  const initialsSize = size === 'lg' ? 'text-3xl' : 'text-2xl';
  const cameraSize = size === 'lg' ? 'h-9 w-9' : 'h-8 w-8';
  const cameraIconSize = size === 'lg' ? 'h-5 w-5' : 'h-4 w-4';

  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    setError(null);
    const f = e.target.files?.[0];
    e.target.value = '';
    if (!f) return;
    if (!ALLOWED_MIME.includes(f.type)) {
      setError('please pick a jpeg, png, webp, gif, or heic image');
      return;
    }
    if (f.size > MAX_FILE_BYTES) {
      setError('photo must be under 5 MB');
      return;
    }
    setFile(f);
  }

  async function onCrop(blob: Blob) {
    setError(null);
    try {
      const cropped = new File([blob], 'avatar.png', { type: 'image/png' });
      await upload(cropped);
      setFile(null);
    } catch (err) {
      setError(extractError(err));
    }
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative">
        {photoUrl ? (
          <img src={photoUrl} alt="" className={cn(avatarSize, 'rounded-full object-cover')} />
        ) : (
          <span
            aria-hidden="true"
            className={cn(
              avatarSize,
              initialsSize,
              'bg-surface-active text-foreground-tertiary flex items-center justify-center rounded-full',
            )}
          >
            {initials}
          </span>
        )}
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          aria-label={photoUrl ? 'change photo' : 'upload photo'}
          className={cn(
            cameraSize,
            'border-border bg-surface text-foreground hover:bg-surface-dim absolute right-0 bottom-0 inline-flex items-center justify-center rounded-full border shadow-sm transition-colors',
          )}
        >
          <CameraIcon className={cameraIconSize} />
        </button>
        <input
          ref={inputRef}
          type="file"
          accept={ALLOWED_MIME.join(',')}
          onChange={onPick}
          className="hidden"
          aria-label="choose profile photo"
        />
      </div>
      {error ? (
        <p role="alert" className="text-xs text-red-600">
          {error}
        </p>
      ) : null}

      {file ? (
        <ImageCropDialog
          file={file}
          shape="round"
          onCancel={() => {
            setFile(null);
          }}
          onCrop={onCrop}
        />
      ) : null}
    </div>
  );
}

function CameraIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
      <circle cx="12" cy="13" r="4" />
    </svg>
  );
}

function extractError(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  return "couldn't upload photo — try again";
}
