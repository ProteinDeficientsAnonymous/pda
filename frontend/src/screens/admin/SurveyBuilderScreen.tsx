import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  useAdminSurvey,
  useDeleteSurveyQuestion,
  useReorderSurveyQuestions,
  useUpdateSurvey,
  type SurveyQuestion,
} from '@/api/surveyAdmin';
import { Button } from '@/components/ui/Button';
import { SortableList } from '@/components/SortableList';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { SurveyQuestionDialog } from './SurveyQuestionDialog';

export default function SurveyBuilderScreen() {
  const { id } = useParams<{ id: string }>();
  const surveyId = id ?? '';
  const { data: survey, isPending, isError } = useAdminSurvey(surveyId);
  const update = useUpdateSurvey(surveyId);
  const reorder = useReorderSurveyQuestions(surveyId);
  const del = useDeleteSurveyQuestion(surveyId);

  const [editing, setEditing] = useState<SurveyQuestion | null>(null);
  const [creating, setCreating] = useState(false);

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load survey — try refreshing" />;

  const currentSurvey = survey;

  function onReorder(nextIds: string[]) {
    reorder.mutate(nextIds);
  }

  function askDelete(q: SurveyQuestion) {
    if (!window.confirm(`delete "${q.label}"? this also deletes responses to it.`)) return;
    del.mutate(q.id);
  }

  function toggleActive() {
    update.mutate({ isActive: !currentSurvey.isActive });
  }

  return (
    <ContentContainer>
      <header className="mb-2 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-medium tracking-tight">{currentSurvey.title}</h1>
          <p className="text-muted text-sm">
            /{currentSurvey.slug} · {currentSurvey.visibility}
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to={`/surveys/${currentSurvey.slug}`}
            className="text-foreground-secondary hover:bg-surface-dim inline-flex h-10 items-center rounded-md px-4 text-sm"
          >
            preview
          </Link>
          <Link
            to={`/admin/surveys/${surveyId}/responses`}
            className="text-foreground-secondary hover:bg-surface-dim inline-flex h-10 items-center rounded-md px-4 text-sm"
          >
            responses
          </Link>
          <Button
            variant="secondary"
            onClick={() => {
              toggleActive();
            }}
          >
            {currentSurvey.isActive ? 'close survey' : 'reopen'}
          </Button>
        </div>
      </header>

      {currentSurvey.pollResult ? (
        <div className="bg-surface-dim text-foreground-secondary mb-6 rounded-md px-3 py-2 text-sm">
          this poll has been finalized — the survey is locked
        </div>
      ) : null}

      <section className="mt-6">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-base font-medium">questions</h2>
          <Button
            onClick={() => {
              setCreating(true);
            }}
          >
            add question
          </Button>
        </div>

        {currentSurvey.questions.length === 0 ? (
          <p className="text-muted text-sm">no questions yet</p>
        ) : (
          <SortableList
            items={currentSurvey.questions}
            onReorder={onReorder}
            ariaLabel="survey questions"
            renderItem={(q) => (
              <article className="border-border bg-surface flex items-center justify-between gap-3 rounded-lg border p-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">
                    {q.label}
                    {q.required ? (
                      <span className="text-muted ms-1 text-xs">· required</span>
                    ) : null}
                  </p>
                  <p className="text-muted text-xs">
                    {q.fieldType}
                    {q.options.length > 0 ? ` · ${String(q.options.length)} options` : ''}
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
      </section>

      <SurveyQuestionDialog
        surveyId={surveyId}
        open={creating}
        onClose={() => {
          setCreating(false);
        }}
      />
      <SurveyQuestionDialog
        surveyId={surveyId}
        open={editing !== null}
        onClose={() => {
          setEditing(null);
        }}
        existing={editing ?? undefined}
      />
    </ContentContainer>
  );
}
