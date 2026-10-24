import { format } from 'date-fns';
import { Link, useNavigate } from 'react-router-dom';

import { type SurveySummary, useAdminSurveys, useDeleteSurvey } from '@/api/surveyAdmin';
import { Button } from '@/components/ui/Button';
import { useConfirm } from '@/components/ui/useConfirm';
import { type SurveyStatus, surveyStatus, surveyVisibilityLabel } from '@/models/survey';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { cn } from '@/utils/cn';

import { SurveyCopyLinkButton } from './SurveyCopyLinkButton';

export default function SurveyAdminListScreen() {
  const { data = [], isPending, isError } = useAdminSurveys();
  const del = useDeleteSurvey();
  const navigate = useNavigate();
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
            void navigate('/admin/surveys/new');
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
          /{survey.slug} · {surveyVisibilityLabel(survey.visibility)} ·{' '}
          {String(survey.responseCount)} responses ·{' '}
          {format(new Date(survey.createdAt), 'MMM d, yyyy').toLowerCase()}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-1">
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
