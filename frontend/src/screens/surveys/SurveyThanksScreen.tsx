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
          {survey?.myResponseId ? (
            <Link
              to={`/surveys/${slug ?? ''}`}
              className="bg-surface text-foreground border-border-strong hover:bg-background inline-flex h-10 items-center rounded-md border px-4 text-sm font-medium"
            >
              edit your response
            </Link>
          ) : null}
          <Link
            to="/"
            className="bg-brand-600 text-brand-on hover:bg-brand-700 inline-flex h-10 items-center rounded-md px-4 text-sm font-medium"
          >
            back to home
          </Link>
        </div>
      </div>
    </ContentContainer>
  );
}
