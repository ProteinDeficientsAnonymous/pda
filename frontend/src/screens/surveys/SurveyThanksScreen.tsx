import { Link, useParams } from 'react-router-dom';

import { useSurvey } from '@/api/surveys';
import { thankYouMessage } from '@/models/survey';
import { ContentContainer, ContentLoading } from '@/screens/public/ContentContainer';

export default function SurveyThanksScreen() {
  const { slug } = useParams<{ slug: string }>();
  const { data: survey, isPending } = useSurvey(slug);
  if (isPending) return <ContentLoading />;
  return (
    <ContentContainer>
      <div className="flex flex-col items-center gap-4 text-center">
        <div aria-hidden="true" className="text-4xl">
          🌱
        </div>
        <h1 className="text-xl font-medium tracking-tight whitespace-pre-wrap">
          {thankYouMessage(survey?.confirmationMessage ?? '')}
        </h1>
        <div className="mt-2 flex flex-wrap justify-center gap-2">
          <Link
            to={`/surveys/${slug ?? ''}`}
            className="text-foreground-secondary hover:bg-surface-dim inline-flex h-10 items-center rounded-md px-4 text-sm"
          >
            edit your response
          </Link>
          <Link
            to="/"
            className="text-foreground-secondary hover:bg-surface-dim inline-flex h-10 items-center rounded-md px-4 text-sm"
          >
            back to home
          </Link>
        </div>
      </div>
    </ContentContainer>
  );
}
