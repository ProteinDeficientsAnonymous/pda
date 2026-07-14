import { type SyntheticEvent, useState } from 'react';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import { useTentativeApprovalMessage, useUpdateTentativeApprovalMessage } from '@/api/content';
import { Button } from '@/components/ui/Button';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { cn } from '@/utils/cn';

const MAX_LENGTH = 4000;

export default function TentativeApprovalMessageScreen() {
  const { data, isPending, isError } = useTentativeApprovalMessage();

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load the message — try refreshing" />;

  return (
    <ContentContainer>
      <h1 className="mb-2 text-2xl font-medium tracking-tight">tentative approval message</h1>
      <p className="text-foreground-secondary mb-6 text-sm">
        sent when someone who came in person gets fully approved — this replaces the default
        confirmation text.
      </p>
      <EditorForm key={data.body} initialBody={data.body} />
    </ContentContainer>
  );
}

function EditorForm({ initialBody }: { initialBody: string }) {
  const update = useUpdateTentativeApprovalMessage();
  const [body, setBody] = useState(initialBody);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setFormError(null);
    if (!body.trim()) {
      setFormError('message body is required');
      return;
    }
    try {
      await update.mutateAsync(body);
      toast.success('message saved 🌱');
    } catch (err) {
      setFormError(extractApiErrorOr(err, "couldn't save the message — try again"));
    }
  }

  const overLimit = body.length > MAX_LENGTH;
  const nearLimit = body.length > MAX_LENGTH * 0.9;

  return (
    <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-3">
      <p className="text-muted text-xs">
        available placeholder:{' '}
        <code className="bg-surface-dim rounded px-1">{'${FIRST_NAME}'}</code> (recipient's first
        name)
      </p>
      <textarea
        value={body}
        onChange={(e) => {
          setBody(e.target.value);
        }}
        rows={10}
        className="border-border bg-background text-foreground focus-visible:ring-brand-200 w-full rounded-md border p-3 font-mono text-sm focus-visible:ring-2 focus-visible:outline-none"
        aria-label="tentative approval message body"
      />
      <div
        className={cn(
          'text-right text-xs',
          overLimit ? 'text-red-600' : nearLimit ? 'text-warning' : 'text-muted',
        )}
      >
        {body.length} / {MAX_LENGTH}
      </div>
      {formError ? (
        <p role="alert" className="text-sm text-red-600">
          {formError}
        </p>
      ) : null}
      <div className="mt-2 flex justify-end gap-2">
        <Button type="submit" disabled={update.isPending || overLimit}>
          {update.isPending ? 'saving…' : 'save'}
        </Button>
      </div>
    </form>
  );
}
