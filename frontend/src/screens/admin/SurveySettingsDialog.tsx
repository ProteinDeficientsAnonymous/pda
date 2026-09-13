import type { SyntheticEvent } from 'react';
import { useState } from 'react';

import { extractApiErrorOr, getFieldError } from '@/api/apiErrors';
import { type Survey, useUpdateSurvey } from '@/api/surveyAdmin';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';

import { SurveyFields, type SurveyFormValues } from './SurveyFields';

interface Props {
  survey: Survey;
  open: boolean;
  onClose: () => void;
}

export function SurveySettingsDialog(props: Props) {
  if (!props.open) return null;
  return <SurveySettingsDialogBody {...props} />;
}

function SurveySettingsDialogBody({ survey, open, onClose }: Props) {
  const update = useUpdateSurvey(survey.id);
  const [values, setValues] = useState<SurveyFormValues>({
    title: survey.title,
    description: survey.description,
    slug: survey.slug,
    visibility: survey.visibility,
    oneResponsePerUser: survey.oneResponsePerUser,
    linkedEventId: survey.linkedEventId,
  });
  const [error, setError] = useState<string | null>(null);
  const [slugError, setSlugError] = useState<string | null>(null);

  async function submit(e: SyntheticEvent) {
    e.preventDefault();
    setError(null);
    setSlugError(null);
    if (!values.title.trim() || !values.slug.trim()) {
      setError('title and slug are required');
      return;
    }
    try {
      await update.mutateAsync(values);
      onClose();
    } catch (err) {
      const slugMessage = getFieldError(err, 'slug');
      if (slugMessage) setSlugError(slugMessage);
      else setError(extractApiErrorOr(err, "couldn't save settings — try again"));
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="survey settings">
      <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-3">
        <SurveyFields
          values={values}
          onChange={(patch) => {
            setValues((v) => ({ ...v, ...patch }));
          }}
          slugError={slugError ?? undefined}
        />
        {error ? (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        ) : null}
        <div className="mt-2 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose} disabled={update.isPending} type="button">
            cancel
          </Button>
          <Button type="submit" disabled={update.isPending}>
            {update.isPending ? 'saving…' : 'save'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
