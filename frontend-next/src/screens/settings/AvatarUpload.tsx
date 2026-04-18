import { useRef, useState } from 'react';
import { isAxiosError } from 'axios';
import { Button } from '@/components/ui/Button';
import { ImageCropDialog } from '@/components/ImageCropDialog';
import { useAuthStore } from '@/auth/store';

const MAX_FILE_BYTES = 5 * 1024 * 1024;
const ALLOWED_MIME = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/gif',
  'image/heic',
  'image/heif',
];

export function AvatarUpload() {
  const user = useAuthStore((s) => s.user);
  const upload = useAuthStore((s) => s.uploadProfilePhoto);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!user) return null;
  const initials = user.displayName.slice(0, 2).toUpperCase() || '?';
  const photoUrl = user.profilePhotoUrl
    ? user.photoUpdatedAt
      ? `${user.profilePhotoUrl}?v=${encodeURIComponent(user.photoUpdatedAt)}`
      : user.profilePhotoUrl
    : '';

  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    setError(null);
    const f = e.target.files?.[0];
    e.target.value = ''; // allow re-picking the same file
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
    <div className="flex items-center gap-4">
      {photoUrl ? (
        <img src={photoUrl} alt="" className="h-16 w-16 rounded-full object-cover" />
      ) : (
        <span
          aria-hidden="true"
          className="flex h-16 w-16 items-center justify-center rounded-full bg-neutral-200 text-xl text-neutral-600"
        >
          {initials}
        </span>
      )}
      <div className="flex flex-col gap-1">
        <input
          ref={inputRef}
          type="file"
          accept={ALLOWED_MIME.join(',')}
          onChange={onPick}
          className="hidden"
          aria-label="choose profile photo"
        />
        <Button variant="secondary" onClick={() => inputRef.current?.click()}>
          {photoUrl ? 'change photo' : 'upload photo'}
        </Button>
        {error ? (
          <p role="alert" className="text-xs text-red-600">
            {error}
          </p>
        ) : null}
      </div>

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

function extractError(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  return "couldn't upload photo — try again";
}
