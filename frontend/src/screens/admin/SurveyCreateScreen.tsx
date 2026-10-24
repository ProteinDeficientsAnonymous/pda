import type { SyntheticEvent } from 'react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { extractApiErrorOr } from '@/api/apiErrors';
import { type SurveyInput, useCreateSurvey } from '@/api/surveyAdmin';
import { Button } from '@/components/ui/Button';
import { ContentContainer } from '@/screens/public/ContentContainer';

import { SurveyFields } from './SurveyFields';
import { useSurveyFieldErrors } from './useSurveyFieldErrors';

const EMPTY_SURVEY: SurveyInput = {
  title: '',
  description: '',
  slug: '',
  visibility: 'members_only',
  isActive: true,
  oneResponsePerUser: false,
  anonymous: false,
  confirmationMessage: '',
  opensAt: null,
  closesAt: null,
  maxResponses: null,
  linkedEventId: null,
};

export default function SurveyCreateScreen() {
  const create = useCreateSurvey();
  const navigate = useNavigate();
  const [values, setValues] = useState<SurveyInput>(EMPTY_SURVEY);
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
      void navigate(`/admin/surveys/${created.id}`, { replace: true });
    } catch (err) {
      if (!fieldErrors.capture(err)) {
        setError(extractApiErrorOr(err, "couldn't create the survey — try again"));
      }
    }
  }

  return (
    <ContentContainer>
      <header className="mb-6">
        <h1 className="text-2xl font-medium tracking-tight">new survey</h1>
        <p className="text-muted text-sm">you can add questions once it's created</p>
      </header>

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
          <Link
            to="/admin/surveys"
            className="text-foreground-secondary hover:bg-surface-dim inline-flex h-10 items-center rounded-md px-4 text-sm"
          >
            cancel
          </Link>
          <Button type="submit" disabled={create.isPending}>
            {create.isPending ? 'creating…' : 'create'}
          </Button>
        </div>
      </form>
    </ContentContainer>
  );
}
