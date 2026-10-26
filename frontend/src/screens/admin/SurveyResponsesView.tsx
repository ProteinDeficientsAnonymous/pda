import { useState } from 'react';

import type { Survey, SurveyResponseAdmin } from '@/api/surveyAdmin';
import { SegmentedControl } from '@/components/ui/SegmentedControl';

import { SurveyIndividualResponse } from './SurveyIndividualResponse';
import { SurveyResponsesTable } from './SurveyResponsesTable';

const ResponsesView = { Table: 'table', Individual: 'individual' } as const;
type ResponsesView = (typeof ResponsesView)[keyof typeof ResponsesView];

const VIEW_OPTIONS = [
  { value: ResponsesView.Table, label: 'table' },
  { value: ResponsesView.Individual, label: 'individual' },
];

export function SurveyResponsesView(props: {
  survey: Survey;
  responses: SurveyResponseAdmin[];
  onDelete: (response: SurveyResponseAdmin) => void;
}) {
  const [view, setView] = useState<ResponsesView>(ResponsesView.Table);
  return (
    <section>
      <SegmentedControl
        name="survey-responses-view"
        ariaLabel="response view"
        options={VIEW_OPTIONS}
        value={view}
        onChange={setView}
        className="mb-3"
      />
      {view === ResponsesView.Table ? (
        <SurveyResponsesTable {...props} />
      ) : (
        <SurveyIndividualResponse {...props} />
      )}
    </section>
  );
}
