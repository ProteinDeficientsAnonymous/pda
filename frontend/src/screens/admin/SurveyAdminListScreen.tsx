import { format } from 'date-fns';
import type { SyntheticEvent } from 'react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { extractApiErrorOr } from '@/api/apiErrors';
import {
  type SurveyInput,
  type SurveySummary,
  useAdminSurveys,
  useCreateSurvey,
  useDeleteSurvey,
} from '@/api/surveyAdmin';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { useConfirm } from '@/components/ui/useConfirm';
import { type SurveyStatus, surveyStatus } from '@/models/survey';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { cn } from '@/utils/cn';

import { SurveyCopyLinkButton } from './SurveyCopyLinkButton';
import { SurveyFields } from './SurveyFields';
import { useSurveyFieldErrors } from './useSurveyFieldErrors';

export default function SurveyAdminListScreen() {
  const { data = [], isPending, isError } = useAdminSurveys();
  const del = useDeleteSurvey();
  const [creating, setCreating] = useState(false);
  const { confirm, element: confirmElement } = useConfirm();

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load surveys — try refreshing" />;

  async function askDelete(s: SurveySummary) {
    const ok = await confirm({
      title: 'delete survey',
      message: `delete "${s.title}"? this also deletes responses.`,
      confirmLabel: 'delete',
      destructive: true,
    });
    if (!ok) return;
    del.mutate(s.id);
  }

  return (
    <ContentContainer>
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-medium tracking-tight">surveys</h1>
        <Button
          onClick={() => {
            setCreating(true);
          }}
        >
          new survey
        </Button>
      </header>

      {data.length === 0 ? (
        <p className="text-muted text-sm">nothing yet</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {data.map((s) => (
            <li key={s.id}>
              <SurveyRow
                survey={s}
                onDelete={(survey) => {
                  void askDelete(survey);
                }}
              />
            </li>
          ))}
        </ul>
      )}

      <CreateSurveyDialog
        open={creating}
        onClose={() => {
          setCreating(false);
        }}
      />

      {confirmElement}
    </ContentContainer>
  );
}

const STATUS_LABEL: Record<SurveyStatus, string> = {
  active: 'active',
  scheduled: 'scheduled',
  capped: 'at capacity',
  closed: 'closed',
};

const STATUS_CLASS: Record<SurveyStatus, string> = {
  active: 'bg-success-subtle text-success',
  scheduled: 'bg-warning-subtle text-warning',
  capped: 'bg-warning-subtle text-warning',
  closed: 'bg-surface-raised text-foreground-secondary',
};

function SurveyRow({
  survey,
  onDelete,
}: {
  survey: SurveySummary;
  onDelete: (s: SurveySummary) => void;
}) {
  return (
    <article className="border-border bg-surface flex items-center justify-between gap-3 rounded-lg border p-3">
      <div className="min-w-0">
        <Link
          to={`/admin/surveys/${survey.id}`}
          className="text-foreground truncate text-sm font-medium underline"
        >
          {survey.title}
        </Link>
        <p className="text-muted text-xs">
          /{survey.slug} · {survey.visibility} · {String(survey.responseCount)} responses ·{' '}
          {format(new Date(survey.createdAt), 'MMM d, yyyy')}
        </p>
      </div>
      <div className="flex gap-1">
        <span
          className={cn('rounded-full px-2 py-0.5 text-xs', STATUS_CLASS[surveyStatus(survey)])}
        >
          {STATUS_LABEL[surveyStatus(survey)]}
        </span>
        <SurveyCopyLinkButton slug={survey.slug} className="h-9 px-3" />
        <Link
          to={`/admin/surveys/${survey.id}/responses`}
          className="text-foreground-secondary hover:bg-surface-dim inline-flex h-9 items-center rounded-md px-3 text-sm"
        >
          responses
        </Link>
        <Button
          variant="ghost"
          onClick={() => {
            onDelete(survey);
          }}
        >
          delete
        </Button>
      </div>
    </article>
  );
}

interface CreateSurveyDialogProps {
  open: boolean;
  onClose: () => void;
}

// Remount on open so the form starts empty — the parent keeps this mounted while closed.
function CreateSurveyDialog(props: CreateSurveyDialogProps) {
  if (!props.open) return null;
  return <CreateSurveyDialogBody {...props} />;
}

function CreateSurveyDialogBody({ open, onClose }: CreateSurveyDialogProps) {
  const create = useCreateSurvey();
  const navigate = useNavigate();
  const [values, setValues] = useState<SurveyInput>({
    title: '',
    description: '',
    slug: '',
    visibility: 'members_only',
    isActive: true,
    oneResponsePerUser: false,
    opensAt: null,
    closesAt: null,
    maxResponses: null,
    linkedEventId: null,
  });
  const [error, setError] = useState<string | null>(null);
  const fieldErrors = useSurveyFieldErrors();

  async function submit(e: SyntheticEvent) {
    e.preventDefault();
    setError(null);
    fieldErrors.reset();
    if (!values.title.trim() || !values.slug.trim()) {
      setError('title and slug are required');
      return;
    }
    try {
      const created = await create.mutateAsync(values);
      onClose();
      void navigate(`/admin/surveys/${created.id}`);
    } catch (err) {
      if (!fieldErrors.capture(err)) setError(extractError(err));
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="new survey">
      <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-3">
        <SurveyFields
          values={values}
          onChange={(patch) => {
            setValues((v) => ({ ...v, ...patch }));
            fieldErrors.clearFor(patch);
          }}
          slugError={fieldErrors.slugError ?? undefined}
          linkedEventError={fieldErrors.linkedEventError ?? undefined}
        />
        {error ? (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        ) : null}
        <div className="mt-2 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose} disabled={create.isPending} type="button">
            cancel
          </Button>
          <Button type="submit" disabled={create.isPending}>
            {create.isPending ? 'creating…' : 'create'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

function extractError(err: unknown): string {
  return extractApiErrorOr(err, "couldn't complete that action — try again");
}
