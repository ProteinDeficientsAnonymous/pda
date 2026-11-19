import { DEFAULT_THANK_YOU_MESSAGE } from '@/models/survey';

import { SurveyTextCard } from './SurveyTextCard';

interface Props {
  surveyId: string;
  confirmationMessage: string;
}

export function SurveyThankYouCard({ surveyId, confirmationMessage }: Props) {
  return (
    <SurveyTextCard
      surveyId={surveyId}
      field="confirmationMessage"
      value={confirmationMessage}
      title="thank-you page"
      badge="always last"
      label="thank-you message"
      placeholder={DEFAULT_THANK_YOU_MESSAGE}
      hint="shown after someone submits — leave blank for the default"
      rows={2}
      maxLength={1000}
      errorMessage="couldn't save the message — try again"
      className="mt-6"
    />
  );
}
