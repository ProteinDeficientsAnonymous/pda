import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { useAdminSurvey } from '@/api/surveyAdmin';
import type { AnswerValue, Survey } from '@/api/surveys';
import { QuestionField } from '@/components/questions/QuestionField';
import { visibleQuestionIds } from '@/components/questions/questionVisibility';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

export default function SurveyPreviewScreen() {
  const { id: surveyId } = useParams<{ id: string }>();
  const { data: survey, isPending, isError } = useAdminSurvey(surveyId);
  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load the survey — try refreshing" />;
  return <SurveyPreview survey={survey} />;
}

function SurveyPreview({ survey }: { survey: Survey }) {
  const [answers, setAnswers] = useState<Record<string, AnswerValue>>({});
  const visible = visibleQuestionIds(survey.questions, answers);

  return (
    <ContentContainer>
      <Link
        to={`/admin/surveys/${survey.id}`}
        className="text-muted mb-4 inline-block text-sm hover:underline"
      >
        ← back to editing
      </Link>

      <p
        role="status"
        className="bg-surface-dim text-foreground-secondary mb-6 rounded-md px-3 py-2 text-sm"
      >
        preview — answers won't be saved
      </p>

      <h1 className="mb-2 text-2xl font-medium tracking-tight">{survey.title}</h1>
      {survey.description ? (
        <p className="text-foreground-tertiary mb-6 text-sm">{survey.description}</p>
      ) : null}

      {survey.anonymous ? (
        <p className="text-foreground-secondary mb-6 text-sm">
          responses are anonymous — your name isn't saved with your answers
        </p>
      ) : null}

      <div className="flex flex-col gap-5">
        {survey.questions
          .filter((q) => visible.has(q.id))
          .map((q) => (
            <QuestionField
              key={q.id}
              question={q}
              value={answers[q.id]}
              onChange={(v) => {
                setAnswers((a) => ({ ...a, [q.id]: v }));
              }}
            />
          ))}
      </div>
    </ContentContainer>
  );
}
