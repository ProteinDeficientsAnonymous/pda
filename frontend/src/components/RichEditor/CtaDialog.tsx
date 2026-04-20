// Dialog for inserting or editing a CTA button node in the editor.

import { useState, type SyntheticEvent } from 'react';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { ensureHttps } from '@/utils/url';
import type { CtaAttrs, CtaVariant } from './CtaExtension';

interface Props {
  open: boolean;
  initial?: CtaAttrs | null;
  onSubmit: (attrs: CtaAttrs) => void;
  onClose: () => void;
}

const VARIANT_OPTIONS: { value: CtaVariant; label: string }[] = [
  { value: 'primary', label: 'primary' },
  { value: 'secondary', label: 'secondary' },
];

export function CtaDialog({ open, initial, onSubmit, onClose }: Props) {
  if (!open) return null;
  return <CtaDialogBody initial={initial ?? null} onSubmit={onSubmit} onClose={onClose} />;
}

function CtaDialogBody({
  initial,
  onSubmit,
  onClose,
}: {
  initial: CtaAttrs | null;
  onSubmit: (attrs: CtaAttrs) => void;
  onClose: () => void;
}) {
  const [label, setLabel] = useState(initial?.label ?? '');
  const [href, setHref] = useState(initial?.href ?? '');
  const [variant, setVariant] = useState<CtaVariant>(initial?.variant ?? 'primary');
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(e: SyntheticEvent) {
    e.preventDefault();
    const trimmedLabel = label.trim();
    const trimmedHref = href.trim();
    if (!trimmedLabel) {
      setError('label is required');
      return;
    }
    if (!trimmedHref) {
      setError('url is required');
      return;
    }
    onSubmit({ label: trimmedLabel, href: ensureHttps(trimmedHref), variant });
  }

  return (
    <Dialog open onClose={onClose} title={initial ? 'edit button' : 'insert button'}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <TextField
          label="label"
          value={label}
          maxLength={60}
          onChange={(e) => {
            setLabel(e.target.value);
          }}
        />
        <TextField
          label="url"
          placeholder="example.com"
          value={href}
          maxLength={500}
          onChange={(e) => {
            setHref(e.target.value);
          }}
        />
        <Select
          label="variant"
          options={VARIANT_OPTIONS}
          value={variant}
          onChange={(e) => {
            setVariant(e.target.value as CtaVariant);
          }}
        />
        {error ? (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        ) : null}
        <div className="mt-2 flex justify-end gap-2">
          <Button variant="ghost" type="button" onClick={onClose}>
            cancel
          </Button>
          <Button type="submit">{initial ? 'update' : 'insert'}</Button>
        </div>
      </form>
    </Dialog>
  );
}
