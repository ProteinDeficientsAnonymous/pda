import { render, screen } from '@testing-library/react';
import type * as ReactRouterDom from 'react-router-dom';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Survey } from '@/api/surveys';
import { useSubmitSurvey, useSurvey } from '@/api/surveys';

import SurveyScreen from './SurveyScreen';

vi.mock('@/api/surveys', () => ({
  useSurvey: vi.fn(),
  useSubmitSurvey: vi.fn(),
}));

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof ReactRouterDom>();
  return { ...actual, useParams: () => ({ slug: 'feedback' }) };
});

const mockUseSurvey = vi.mocked(useSurvey);
const mockUseSubmitSurvey = vi.mocked(useSubmitSurvey);

function makeSurvey(overrides: Partial<Survey> = {}): Survey {
  return {
    id: 'survey-1',
    title: 'Feedback survey',
    description: '',
    slug: 'feedback',
    visibility: 'members_only',
    isActive: true,
    oneResponsePerUser: false,
    anonymous: false,
    confirmationMessage: '',
    questions: [],
    myResponseId: null,
    myAnswers: null,
    pollResult: null,
    ...overrides,
  };
}

function mockSubmit(overrides: Partial<ReturnType<typeof useSubmitSurvey>> = {}) {
  mockUseSubmitSurvey.mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
    isSuccess: false,
    ...overrides,
  } as unknown as ReturnType<typeof useSubmitSurvey>);
}

beforeEach(() => {
  vi.clearAllMocks();
});

function renderScreen(survey: Survey) {
  mockUseSurvey.mockReturnValue({
    data: survey,
    isPending: false,
    isError: false,
  } as unknown as ReturnType<typeof useSurvey>);
  return render(
    <MemoryRouter>
      <SurveyScreen />
    </MemoryRouter>,
  );
}

describe('SurveyScreen post-submit confirmation', () => {
  it('shows the default confirmation when the survey has no custom message', () => {
    mockSubmit({ isSuccess: true });
    renderScreen(makeSurvey({ confirmationMessage: '' }));
    expect(screen.getByText('saved ✓')).toBeInTheDocument();
  });

  it('shows the survey confirmation message, lowercased, after a successful submit', () => {
    mockSubmit({ isSuccess: true });
    renderScreen(makeSurvey({ confirmationMessage: 'Thanks For Your Feedback!' }));
    expect(screen.getByText('thanks for your feedback!')).toBeInTheDocument();
  });

  it('does not show a confirmation before submitting', () => {
    mockSubmit({ isSuccess: false });
    renderScreen(makeSurvey({ confirmationMessage: 'thanks!' }));
    expect(screen.queryByText('thanks!')).not.toBeInTheDocument();
    expect(screen.queryByText('saved ✓')).not.toBeInTheDocument();
  });
});
