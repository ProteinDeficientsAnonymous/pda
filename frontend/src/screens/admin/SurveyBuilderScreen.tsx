import { useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { extractApiErrorOr } from '@/api/apiErrors';
import {
  type SurveyQuestion,
  useAdminSurvey,
  useCreateSurveyQuestion,
  useDeleteSurveyQuestion,
  useReorderSurveyQuestions,
  useUpdateSurvey,
} from '@/api/surveyAdmin';
import { DEFAULT_SURVEY_QUESTION_TYPE } from '@/api/surveys';
import { SortableList } from '@/components/SortableList';
import { Button } from '@/components/ui/Button';
import { useConfirm } from '@/components/ui/useConfirm';
import { SURVEY_PREVIEW_PARAM, surveyVisibilityLabel } from '@/models/survey';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { SurveyCopyLinkButton } from './SurveyCopyLinkButton';
import { SurveyQuestionCard } from './SurveyQuestionCard';
import { SurveySettingsDialog } from './SurveySettingsDialog';

export default function SurveyBuilderScreen() {
  const { id } = useParams<{ id: string }>();
  const surveyId = id ?? '';
  const { data: survey, isPending, isError } = useAdminSurvey(surveyId);
  const update = useUpdateSurvey(surveyId);
  const reorder = useReorderSurveyQuestions(surveyId);
  const del = useDeleteSurveyQuestion(surveyId);
  const create = useCreateSurveyQuestion(surveyId);

  const [focusId, setFocusId] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  // A ref, not isPending: a fast second click can land before the pending state renders.
  const duplicating = useRef(false);
  const { confirm, element: confirmElement } = useConfirm();

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load survey — try refreshing" />;

  const currentSurvey = survey;

  function onReorder(nextIds: string[]) {
    reorder.mutate(nextIds);
  }

  async function askDelete(q: SurveyQuestion) {
    const dependents = currentSurvey.questions
      .filter((other) => other.showIf?.questionId === q.id)
      .map((other) => `"${other.label}"`);
    const conditionNote = dependents.length
      ? ` ${dependents.join(', ')} will lose ${dependents.length === 1 ? 'its condition' : 'their conditions'} and always show.`
      : '';
    const ok = await confirm({
      title: 'delete question',
      message: `delete "${q.label}"? this also deletes responses to it.${conditionNote}`,
      confirmLabel: 'delete',
      destructive: true,
    });
    if (!ok) return;
    del.mutate(q.id);
  }

  async function addQuestion() {
    const created = await create.mutateAsync({
      label: 'untitled question',
      fieldType: DEFAULT_SURVEY_QUESTION_TYPE,
      options: [],
      required: false,
      showIf: null,
    });
    setFocusId(created.id);
  }

  async function duplicate(q: SurveyQuestion) {
    if (duplicating.current) return;
    duplicating.current = true;
    try {
      const created = await create.mutateAsync({
        label: q.label,
        fieldType: q.fieldType,
        options: q.options,
        required: q.required,
        showIf: q.showIf ?? null,
      });
      const ids = currentSurvey.questions.map((other) => other.id);
      ids.splice(ids.indexOf(q.id) + 1, 0, created.id);
      await reorder.mutateAsync(ids);
      setFocusId(created.id);
    } finally {
      duplicating.current = false;
    }
  }

  async function toggleActive() {
    if (currentSurvey.isActive) {
      const ok = await confirm({
        title: 'close survey',
        message: `close "${currentSurvey.title}"? it'll stop taking new responses until you reopen it — existing responses stay put`,
        confirmLabel: 'close survey',
      });
      if (!ok) return;
    }
    update.mutate({ isActive: !currentSurvey.isActive });
  }

  return (
    <ContentContainer>
      <Link to="/admin/surveys" className="text-muted mb-4 inline-block text-sm hover:underline">
        ← back to surveys
      </Link>

      <header className="mb-2 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-medium tracking-tight">{currentSurvey.title}</h1>
          <p className="text-muted text-sm">
            /{currentSurvey.slug} · {surveyVisibilityLabel(currentSurvey.visibility)}
            {currentSurvey.isActive ? null : ' · closed'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <SurveyCopyLinkButton slug={currentSurvey.slug} />
          <Link
            to={`/surveys/${currentSurvey.slug}?${SURVEY_PREVIEW_PARAM}=1`}
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
            variant="ghost"
            onClick={() => {
              setSettingsOpen(true);
            }}
          >
            settings
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              void toggleActive();
            }}
          >
            {currentSurvey.isActive ? 'close survey' : 'reopen survey'}
          </Button>
        </div>
      </header>

      {currentSurvey.pollResult ? (
        <div className="bg-surface-dim text-foreground-secondary mb-6 rounded-md px-3 py-2 text-sm">
          this poll has been finalized
        </div>
      ) : null}

      <section className="mt-6">
        <h2 className="mb-3 text-base font-medium">questions</h2>

        {reorder.isError ? (
          <p role="alert" className="text-destructive mb-2 text-sm">
            {extractApiErrorOr(reorder.error, "couldn't reorder questions — try again")}
          </p>
        ) : null}

        {currentSurvey.questions.length === 0 ? (
          <p className="text-muted mb-3 text-sm">no questions yet 🌿</p>
        ) : (
          <SortableList
            items={currentSurvey.questions}
            onReorder={onReorder}
            ariaLabel="survey questions"
            renderItem={(q) => (
              <SurveyQuestionCard
                surveyId={surveyId}
                question={q}
                questions={currentSurvey.questions}
                focusOnMount={q.id === focusId}
                onDuplicate={() => {
                  void duplicate(q).catch(() => undefined);
                }}
                onDelete={() => {
                  void askDelete(q);
                }}
              />
            )}
          />
        )}

        {create.isError ? (
          <p role="alert" className="text-destructive mt-2 text-sm">
            {extractApiErrorOr(create.error, "couldn't add the question — try again")}
          </p>
        ) : null}

        <button
          type="button"
          disabled={create.isPending}
          onClick={() => {
            void addQuestion().catch(() => undefined);
          }}
          className="border-border-strong text-foreground-secondary hover:bg-surface-dim mt-3 w-full rounded-lg border border-dashed py-3 text-sm transition-colors disabled:opacity-50"
        >
          {create.isPending ? 'adding…' : '+ add question'}
        </button>
      </section>

      <SurveySettingsDialog
        survey={currentSurvey}
        open={settingsOpen}
        onClose={() => {
          setSettingsOpen(false);
        }}
      />

      {confirmElement}
    </ContentContainer>
  );
}
