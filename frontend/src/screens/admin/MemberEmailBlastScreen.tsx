import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';

import { extractApiErrorOr, getApiStatus, hasErrorCode } from '@/api/apiErrors';
import {
  type BlastPreview,
  type MemberBlast,
  useBlastPreview,
  useMemberBlasts,
  useSendMemberBlast,
  useSendTestBlast,
} from '@/api/memberBlast';
import { RichEditor } from '@/components/RichEditor/RichEditor';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';
import { useConfirm } from '@/components/ui/useConfirm';
import { ContentContainer } from '@/screens/public/ContentContainer';

import { MemberBlastHistory } from './MemberBlastHistory';

const UNCERTAIN =
  'something went wrong — the blast may have gone out. check the history below before resending.';

const RESULT_COPY: Record<string, (r: MemberBlast) => string> = {
  unknown: () => "brevo didn't confirm delivery — check brevo before resending",
  failed: () => 'nothing was sent — try again',
};

function sendErrorMessage(err: unknown): string {
  if (hasErrorCode(err, 'notification.blast_duplicate')) {
    return 'this was already sent in the last 15 minutes';
  }
  const status = getApiStatus(err);
  if (status !== null && status < 500) return extractApiErrorOr(err, "couldn't send — try again");
  return UNCERTAIN;
}

export default function MemberEmailBlastScreen() {
  const [subject, setSubject] = useState('');
  const [json, setJson] = useState('');
  const [html, setHtml] = useState('');
  const [preview, setPreview] = useState<BlastPreview | null>(null);
  const [result, setResult] = useState<MemberBlast | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const sendingRef = useRef(false);
  const previewMut = useBlastPreview();
  const testMut = useSendTestBlast();
  const sendMut = useSendMemberBlast();
  const history = useMemberBlasts();
  const { confirm, element } = useConfirm();
  const payload = { subject: subject.trim(), body_html: html };
  useEffect(() => {
    setPreview(null);
  }, [subject, html]);
  const ready = payload.subject !== '' && html.replace(/<(?!img)[^>]*>/g, '').trim() !== '';

  async function run<T>(fn: () => Promise<T>, fallback: string): Promise<T | null> {
    setError(null);
    try {
      return await fn();
    } catch (err) {
      setError(extractApiErrorOr(err, fallback));
      return null;
    }
  }

  async function onSend() {
    if (sendingRef.current) return;
    sendingRef.current = true;
    setSending(true);
    setResult(null);
    try {
      const fresh = await run(() => previewMut.mutateAsync(payload), "couldn't load preview");
      if (!fresh) return;
      setPreview(fresh);
      const ok = await confirm({
        message: `send "${payload.subject}" to ${String(fresh.recipient_count)} members?`,
        confirmLabel: 'send',
      });
      if (!ok) return;
      try {
        setResult(await sendMut.mutateAsync(payload));
      } catch (err) {
        setError(sendErrorMessage(err));
        void history.refetch();
      }
    } finally {
      sendingRef.current = false;
      setSending(false);
    }
  }

  const onPreview = async () =>
    setPreview(await run(() => previewMut.mutateAsync(payload), "couldn't load preview"));
  const onTest = async () => {
    if (await run(() => testMut.mutateAsync(payload), "couldn't send test")) {
      toast.success('test sent to your email');
    }
  };
  const actions: [string, () => Promise<void>, boolean][] = [
    ['preview', onPreview, previewMut.isPending],
    ['send test to me', onTest, testMut.isPending],
    ['send to all members', onSend, sending || sendMut.isPending],
  ];

  return (
    <ContentContainer>
      <h1 className="text-2xl font-medium tracking-tight">email blast</h1>
      <div className="mt-4 flex flex-col gap-3">
        <TextField
          label="subject"
          value={subject}
          onChange={(e) => {
            setSubject(e.target.value);
          }}
        />
        <RichEditor value={json} onChange={setJson} onHtmlChange={setHtml} />
        <div className="flex flex-wrap gap-2">
          {actions.map(([label, go, busy], i) => (
            <Button
              key={label}
              variant={i === 2 ? 'primary' : 'ghost'}
              onClick={() => void go()}
              disabled={!ready || busy}
            >
              {label}
            </Button>
          ))}
        </div>
        {error ? (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        ) : null}
        {result ? (
          <p role="status" className="text-sm">
            {RESULT_COPY[result.status]?.(result) ?? `sent to ${String(result.sent_count)} members`}
          </p>
        ) : null}
        {preview ? (
          <>
            <p className="text-muted text-sm">
              this will go to {preview.recipient_count} members ({preview.skipped_count} skipped —
              no or invalid email)
            </p>
            <iframe
              sandbox=""
              srcDoc={preview.html}
              title="email preview"
              className="h-96 w-full rounded-md border"
            />
          </>
        ) : null}
      </div>
      <MemberBlastHistory blasts={history.data ?? []} />
      {element}
    </ContentContainer>
  );
}
