import { useState } from 'react';

import { Button } from '@/components/ui/Button';

import { RSVP_QUESTION_TYPE_LABELS, type RsvpQuestionDraft } from '../rsvpQuestions';
import { EventRsvpQuestionDialog } from './EventRsvpQuestionDialog';

interface Props {
  rsvpEnabled: boolean;
  questions: RsvpQuestionDraft[];
  onQuestionsChange: (next: RsvpQuestionDraft[]) => void;
}

export function EventFormQuestions({ rsvpEnabled, questions, onQuestionsChange }: Props) {
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<RsvpQuestionDraft | null>(null);

  if (!rsvpEnabled) {
    return (
      <p className="text-muted text-sm">enable rsvp to ask guests questions when they respond</p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-muted text-sm">shown when guests rsvp as going or maybe</p>
        <Button
          type="button"
          variant="secondary"
          onClick={() => {
            setCreating(true);
          }}
        >
          add question
        </Button>
      </div>
      {questions.length === 0 ? (
        <p className="text-muted text-sm">no questions yet</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {questions.map((q) => (
            <li key={q.id}>
              <article className="border-border bg-surface flex items-center justify-between gap-3 rounded-lg border p-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">
                    {q.label}
                    {q.required ? (
                      <span className="text-muted ms-1 text-xs">· required</span>
                    ) : null}
                  </p>
                  <p className="text-muted text-xs">
                    {RSVP_QUESTION_TYPE_LABELS[q.fieldType]}
                    {q.options.length > 0 ? ` · ${String(q.options.length)} options` : ''}
                  </p>
                </div>
                <div className="flex shrink-0 gap-1">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => {
                      setEditing(q);
                    }}
                  >
                    edit
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => {
                      onQuestionsChange(questions.filter((item) => item.id !== q.id));
                    }}
                  >
                    delete
                  </Button>
                </div>
              </article>
            </li>
          ))}
        </ul>
      )}

      <EventRsvpQuestionDialog
        open={creating}
        onClose={() => {
          setCreating(false);
        }}
        onSave={(question) => {
          onQuestionsChange([...questions, question]);
        }}
      />
      <EventRsvpQuestionDialog
        open={editing !== null}
        existing={editing ?? undefined}
        onClose={() => {
          setEditing(null);
        }}
        onSave={(question) => {
          onQuestionsChange(questions.map((item) => (item.id === question.id ? question : item)));
        }}
      />
    </div>
  );
}
