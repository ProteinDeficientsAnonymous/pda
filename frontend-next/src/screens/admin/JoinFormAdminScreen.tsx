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
      <p className="mb-6 text-sm text-neutral-600">
        questions shown to applicants on /join. name + phone are always included.
      </p>

      {data.length === 0 ? (
        <p className="text-sm text-neutral-500">no custom questions yet</p>
      ) : (
        <SortableList
          items={data}
          onReorder={handleReorder}
          ariaLabel="join form questions"
          renderItem={(q) => (
            <article className="flex items-center justify-between gap-3 rounded-lg border border-neutral-200 bg-white p-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">
                  {q.label}{' '}
                  {q.required ? <span className="text-xs text-neutral-500">· required</span> : null}
                </p>
                <p className="text-xs text-neutral-500">
                  {q.fieldType}
                  {q.fieldType === 'select' && q.options.length > 0
                    ? ` · ${String(q.options.length)} options`
                    : ''}
                </p>
              </div>
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  onClick={() => {
                    setEditing(q);
                  }}
                >
                  edit
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => {
                    askDelete(q);
                  }}
                >
                  delete
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
