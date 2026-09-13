import { Link } from 'react-router-dom';

import { type SurveyListItem, useSurveys } from '@/api/surveys';
import { useAuthStore } from '@/auth/store';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

export default function SurveysScreen() {
  const { data = [], isPending, isError } = useSurveys();
  const isAuthed = useAuthStore((s) => s.status === 'authed');

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load surveys — try refreshing" />;

  return (
    <ContentContainer>
      <h1 className="mb-2 text-2xl font-medium tracking-tight">surveys</h1>
      <p className="text-foreground-tertiary mb-6 text-sm">
        {isAuthed
          ? 'open surveys and polls — your answers help shape what we do next'
          : 'open surveys — log in to see member-only ones too'}
      </p>

      {data.length === 0 ? (
        <p className="text-muted text-sm">nothing open right now</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {data.map((survey) => (
            <li key={survey.id}>
              <SurveyRow survey={survey} />
            </li>
          ))}
        </ul>
      )}
    </ContentContainer>
  );
}

function SurveyRow({ survey }: { survey: SurveyListItem }) {
  return (
    <Link
      to={`/surveys/${survey.slug}`}
      className="border-border bg-surface hover:bg-surface-dim block rounded-lg border p-3 transition-colors"
    >
      <span className="text-foreground text-sm font-medium [overflow-wrap:anywhere] break-words">
        {survey.title.toLowerCase()}
      </span>
      {survey.description ? (
        <p className="text-foreground-tertiary mt-1 line-clamp-2 text-xs">
          {survey.description.toLowerCase()}
        </p>
      ) : null}
    </Link>
  );
}
