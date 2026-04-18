import { useState } from 'react';
import { format } from 'date-fns';
import { Link, useNavigate } from 'react-router-dom';
import { isAxiosError } from 'axios';
import {
  useAdminSurveys,
  useCreateSurvey,
  useDeleteSurvey,
  type SurveyInput,
  type SurveySummary,
} from '@/api/surveyAdmin';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { Textarea } from '@/components/ui/Textarea';
import { cn } from '@/utils/cn';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

export default function SurveyAdminListScreen() {
  const { data = [], isPending, isError } = useAdminSurveys();
  const del = useDeleteSurvey();
  const [creating, setCreating] = useState(false);

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load surveys — try refreshing" />;

  function askDelete(s: SurveySummary) {
    if (!window.confirm(`delete "${s.title}"? this also deletes responses.`)) return;
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
        <p className="text-sm text-neutral-500">nothing yet</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {data.map((s) => (
            <li key={s.id}>
              <SurveyRow survey={s} onDelete={askDelete} />
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
    </ContentContainer>
  );
}

function SurveyRow({
  survey,
  onDelete,
}: {
  survey: SurveySummary;
  onDelete: (s: SurveySummary) => void;
}) {
  return (
    <article className="flex items-center justify-between gap-3 rounded-lg border border-neutral-200 bg-white p-3">
      <div className="min-w-0">
        <Link
          to={`/admin/surveys/${survey.id}`}
          className="truncate text-sm font-medium text-neutral-900 underline"
        >
          {survey.title}
        </Link>
        <p className="text-xs text-neutral-500">
          /{survey.slug} · {survey.visibility} · {String(survey.responseCount)} responses ·{' '}
          {format(new Date(survey.createdAt), 'MMM d, yyyy')}
        </p>
      </div>
      <div className="flex gap-1">
        <span
          className={cn(
            'rounded-full px-2 py-0.5 text-xs',
            survey.isActive ? 'bg-green-100 text-green-800' : 'bg-neutral-200 text-neutral-700',
          )}
        >
          {survey.isActive ? 'active' : 'closed'}
        </span>
        <Link
          to={`/admin/surveys/${survey.id}/responses`}
          className="inline-flex h-9 items-center rounded-md px-3 text-sm text-neutral-700 hover:bg-neutral-100"
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

function CreateSurveyDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const create = useCreateSurvey();
  const navigate = useNavigate();
  const [values, setValues] = useState<SurveyInput>({
    title: '',
    description: '',
    slug: '',
    visibility: 'members_only',
    isActive: true,
    oneResponsePerUser: false,
    linkedEventId: null,
  });
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.SyntheticEvent) {
    e.preventDefault();
    setError(null);
    if (!values.title.trim() || !values.slug.trim()) {
      setError('title and slug are required');
      return;
    }
    try {
      const created = await create.mutateAsync(values);
      onClose();
      void navigate(`/admin/surveys/${created.id}`);
    } catch (err) {
      setError(extractError(err));
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="new survey">
      <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-3">
        <TextField
          label="title"
          value={values.title}
          onChange={(e) => {
            setValues((v) => ({ ...v, title: e.target.value }));
          }}
          maxLength={200}
        />
        <TextField
          label="slug"
          value={values.slug}
          onChange={(e) => {
            setValues((v) => ({ ...v, slug: e.target.value }));
          }}
          hint="short url segment — /surveys/:slug"
          maxLength={100}
        />
        <Textarea
          label="description (optional)"
          value={values.description}
          onChange={(e) => {
            setValues((v) => ({ ...v, description: e.target.value }));
          }}
          rows={3}
          maxLength={2000}
        />
        <Select
          label="visibility"
          value={values.visibility}
          onChange={(e) => {
            setValues((v) => ({ ...v, visibility: e.target.value }));
          }}
          options={[
            { value: 'members_only', label: 'members only' },
            { value: 'public', label: 'public' },
          ]}
        />
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={values.oneResponsePerUser}
            onChange={(e) => {
              setValues((v) => ({ ...v, oneResponsePerUser: e.target.checked }));
            }}
          />
          <span>one response per user</span>
        </label>
        {error ? (
          <p role="alert" className="text-sm text-red-600">
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
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  return "couldn't complete that action — try again";
}
