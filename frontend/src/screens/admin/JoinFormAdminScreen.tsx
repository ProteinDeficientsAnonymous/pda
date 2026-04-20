// Edit the dynamic join-form questions. Reorder via dnd-kit; optimistic
// update on drop + server PUT; server returns the full list in the new
// order which replaces the optimistic cache.

import { useState } from 'react';
import type { JoinQuestion } from '@/api/join';
import { useDeleteJoinQuestion, useJoinQuestions, useReorderJoinQuestions } from '@/api/join';
import { Button } from '@/components/ui/Button';
import { SortableList } from '@/components/SortableList';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { JoinQuestionDialog } from './JoinQuestionDialog';

export default function JoinFormAdminScreen() {
  const { data = [], isPending, isError } = useJoinQuestions();
  const reorder = useReorderJoinQuestions();
  const del = useDeleteJoinQuestion();
  const [editing, setEditing] = useState<JoinQuestion | null>(null);
  const [creating, setCreating] = useState(false);

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load questions — try refreshing" />;

  function handleReorder(nextIds: string[]) {
    reorder.mutate(nextIds);
  }

  function askDelete(q: JoinQuestion) {
    // Small inline confirm instead of a full dialog — non-destructive-ish
    // (deleting a question doesn't invalidate prior submissions).
    if (!window.confirm(`delete "${q.label}"?`)) return;
    del.mutate(q.id);
  }

  return (
    <ContentContainer>
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-medium tracking-tight">join form</h1>
        <Button
          onClick={() => {
            setCreating(true);
          }}
        >
          add question
        </Button>
      </header>
      <p className="text-foreground-tertiary mb-6 text-sm">
        questions shown to applicants on /join. name + phone are always included.
      </p>

      {data.length === 0 ? (
        <p className="text-muted text-sm">no custom questions yet</p>
      ) : (
        <SortableList
          items={data}
          onReorder={handleReorder}
          ariaLabel="join form questions"
          renderItem={(q) => (
            <article className="border-border bg-surface flex w-full min-w-0 items-center justify-between gap-2 rounded-lg border p-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium break-words">
                  {q.label}
                  {q.required ? <span className="text-muted ml-1 text-xs">· required</span> : null}
                </p>
                <p className="text-muted text-xs break-words">
                  {q.fieldType}
                  {q.fieldType === 'select' && q.options.length > 0
                    ? ` · ${String(q.options.length)} options`
                    : ''}
                </p>
              </div>
              <div className="flex shrink-0 gap-0.5">
                <Button
                  variant="ghost"
                  aria-label={`edit ${q.label}`}
                  onClick={() => {
                    setEditing(q);
                  }}
                  className="!px-2"
                >
                  <PencilIcon />
                </Button>
                <Button
                  variant="ghost"
                  aria-label={`delete ${q.label}`}
                  onClick={() => {
                    askDelete(q);
                  }}
                  className="!px-2"
                >
                  <CloseIcon />
                </Button>
              </div>
            </article>
          )}
        />
      )}

      <JoinQuestionDialog
        open={creating}
        onClose={() => {
          setCreating(false);
        }}
      />
      <JoinQuestionDialog
        open={editing !== null}
        onClose={() => {
          setEditing(null);
        }}
        existing={editing ?? undefined}
      />
    </ContentContainer>
  );
}

function PencilIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
    </svg>
  );
}
