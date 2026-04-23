// Bulk-create dialog for /members. Admin pastes a list of phone numbers
// (one per line) — we normalize each to E.164 using US as the default
// country code and post them to /api/auth/bulk-create-users/. The result
// view lists one-time magic-login links for each newly created row and
// any per-row errors so the admin can retry the failed entries.

import { useState, type SyntheticEvent } from 'react';
import { isAxiosError } from 'axios';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Textarea } from '@/components/ui/Textarea';
import { useBulkCreateUsers, type BulkCreateResponse, type BulkCreateResult } from '@/api/users';
import { formatPhone } from '@/utils/formatPhone';
import { buildMagicLinkUrl, buildSmsHref, buildWelcomeMessage } from '@/utils/welcomeMessage';

interface Props {
  open: boolean;
  onClose: () => void;
}

export function BulkCreateDialog({ open, onClose }: Props) {
  const bulkCreate = useBulkCreateUsers();
  const [raw, setRaw] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [response, setResponse] = useState<BulkCreateResponse | null>(null);

  function handleClose() {
    setRaw('');
    setFormError(null);
    setResponse(null);
    onClose();
  }

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setFormError(null);
    const numbers = parseNumbers(raw);
    if (numbers.length === 0) {
      setFormError('add at least one phone number');
      return;
    }
    try {
      const result = await bulkCreate.mutateAsync(numbers);
      setResponse(result);
    } catch (err) {
      setFormError(extractError(err));
    }
  }

  if (response) {
    return <ResultsView open={open} response={response} onClose={handleClose} />;
  }

  return (
    <Dialog open={open} onClose={handleClose} title="bulk add members">
      <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-3">
        <Textarea
          label="phone numbers"
          hint="one per line — US numbers assumed unless prefixed with + and a country code"
          value={raw}
          rows={8}
          placeholder={'555-123-4567\n+44 20 7946 0958'}
          onChange={(e) => {
            setRaw(e.target.value);
          }}
        />
        {formError ? (
          <p role="alert" className="text-sm text-red-600">
            {formError}
          </p>
        ) : null}
        <div className="mt-2 flex justify-end gap-2">
          <Button variant="ghost" onClick={handleClose} type="button">
            cancel
          </Button>
          <Button type="submit" disabled={bulkCreate.isPending}>
            {bulkCreate.isPending ? 'creating…' : 'create members'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

function ResultsView({
  open,
  response,
  onClose,
}: {
  open: boolean;
  response: BulkCreateResponse;
  onClose: () => void;
}) {
  const successes = response.results.filter((r) => r.success);
  const failures = response.results.filter((r) => !r.success);

  return (
    <Dialog open={open} onClose={onClose} title="bulk results">
      <p className="text-sm text-neutral-700">
        created {response.created} of {response.created + response.failed} — share each magic link
        with its recipient; links won't be shown again.
      </p>

      {successes.length > 0 ? (
        <section className="mt-4">
          <h3 className="mb-2 text-xs font-medium tracking-wide text-neutral-500">created</h3>
          <ul className="flex flex-col gap-2">
            {successes.map((r) => (
              <li key={r.row}>
                <MagicLinkRow result={r} />
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {failures.length > 0 ? (
        <section className="mt-4">
          <h3 className="mb-2 text-xs font-medium tracking-wide text-neutral-500">failed</h3>
          <ul className="flex flex-col gap-1">
            {failures.map((r) => (
              <li key={r.row} className="text-sm text-red-700">
                {formatPhone(r.phoneNumber)} — {r.error ?? 'unknown error'}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className="mt-4 flex justify-end">
        <Button onClick={onClose}>done</Button>
      </div>
    </Dialog>
  );
}

function MagicLinkRow({ result }: { result: BulkCreateResult }) {
  const [copied, setCopied] = useState(false);
  const url = result.magicLinkToken ? buildMagicLinkUrl(result.magicLinkToken) : '';
  const smsHref = url ? buildSmsHref(result.phoneNumber, buildWelcomeMessage(null, url)) : '';

  async function copy() {
    if (!url) return;
    await navigator.clipboard.writeText(url);
    setCopied(true);
    window.setTimeout(() => {
      setCopied(false);
    }, 2000);
  }

  return (
    <div className="flex flex-col gap-1 rounded-md border border-neutral-200 bg-white p-2">
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-sm font-medium text-neutral-900">
          {formatPhone(result.phoneNumber)}
        </span>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => void copy()}>
            {copied ? 'copied ✓' : 'copy link'}
          </Button>
          {smsHref ? (
            <a
              href={smsHref}
              className="focus-visible:ring-brand-200 bg-surface text-foreground border-border-strong hover:bg-background inline-flex h-10 items-center justify-center rounded-md border px-4 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none"
            >
              send welcome message
            </a>
          ) : null}
        </div>
      </div>
      {url ? (
        <code className="overflow-x-auto rounded bg-neutral-100 px-2 py-1 text-xs break-all">
          {url}
        </code>
      ) : null}
    </div>
  );
}

function parseNumbers(raw: string): string[] {
  return raw
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map(normalizePhone);
}

function normalizePhone(input: string): string {
  const trimmed = input.trim();
  if (trimmed.startsWith('+')) return trimmed;
  const digits = trimmed.replace(/\D/g, '');
  if (digits.length === 0) return trimmed;
  if (digits.length === 10) return `+1${digits}`;
  if (digits.length === 11 && digits.startsWith('1')) return `+${digits}`;
  return `+${digits}`;
}

function extractError(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  return "couldn't create members — try again";
}
