import { Link, useParams } from 'react-router-dom';

import { useSurvey } from '@/api/surveys';
import { buttonClass } from '@/components/ui/buttonClass';
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
            <Link to={`/surveys/${slug ?? ''}`} className={buttonClass('secondary')}>
              edit your response
            </Link>
          ) : null}
          <Link to="/" className={buttonClass()}>
            back to home
          </Link>
        </div>
      </div>
    </ContentContainer>
  );
}
