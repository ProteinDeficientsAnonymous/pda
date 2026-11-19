import { SurveyTextCard } from './SurveyTextCard';

interface Props {
  surveyId: string;
  description: string;
}

export function SurveyDescriptionCard({ surveyId, description }: Props) {
  return (
    <SurveyTextCard
      surveyId={surveyId}
      field="description"
      value={description}
      title="intro"
      badge="always first"
      label="description"
      hint="shown under the title, before the questions — optional"
      rows={3}
      maxLength={2000}
      errorMessage="couldn't save the description — try again"
      className="mb-3"
    />
  );
}
