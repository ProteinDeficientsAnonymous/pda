import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type * as SurveysApi from '@/api/surveys';
import { ShowIfOperator, type Survey } from '@/api/surveys';

const submitMutate = vi.fn();
const useSurveyMock = vi.fn();

vi.mock('@/api/surveys', async (importOriginal) => {
  const actual = await importOriginal<typeof SurveysApi>();
  return {
    ...actual,
    useSurvey: (slug: string | undefined) => useSurveyMock(slug) as unknown,
    useSubmitSurvey: () => ({
      mutateAsync: submitMutate,
      isPending: false,
      isSuccess: false,
    }),
  };
});

const { default: SurveyScreen } = await import('./SurveyScreen');

const survey: Survey = {
  id: 's1',
  title: 'diet survey',
  description: '',
  slug: 'diet',
  visibility: 'public',
  isActive: true,
  oneResponsePerUser: false,
  myResponseId: null,
  myAnswers: null,
  pollResult: null,
  questions: [
    {
      id: 'diet',
      label: 'diet',
      fieldType: 'radio',
      options: ['vegan', 'veg'],
      required: false,
      displayOrder: 0,
      showIf: null,
    },
    {
      id: 'why',
      label: 'why vegan',
      fieldType: 'text',
      options: [],
      required: true,
      displayOrder: 1,
      showIf: { questionId: 'diet', operator: ShowIfOperator.Equals, value: 'vegan' },
    },
  ],
};

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={['/surveys/diet']}>
      <SurveyScreen />
    </MemoryRouter>,
  );
}

describe('SurveyScreen conditional questions', () => {
  beforeEach(() => {
    submitMutate.mockReset();
    submitMutate.mockResolvedValue({});
    useSurveyMock.mockReturnValue({ data: survey, isPending: false, isError: false });
  });

  it('hides a question whose condition is not met', () => {
    renderScreen();
    expect(screen.getByRole('radio', { name: 'vegan' })).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: /why vegan/ })).not.toBeInTheDocument();
  });

  it('reveals the question once the condition holds', async () => {
    const user = userEvent.setup();
    renderScreen();
    await user.click(screen.getByRole('radio', { name: 'vegan' }));
    expect(screen.getByRole('textbox', { name: /why vegan/ })).toBeInTheDocument();
  });

  it('skips validation for a hidden required question', async () => {
    const user = userEvent.setup();
    renderScreen();
    await user.click(screen.getByRole('radio', { name: 'veg' }));
    await user.click(screen.getByRole('button', { name: 'submit' }));
    expect(submitMutate).toHaveBeenCalledWith({ diet: 'veg' });
  });

  it('validates the question once it is visible', async () => {
    const user = userEvent.setup();
    renderScreen();
    await user.click(screen.getByRole('radio', { name: 'vegan' }));
    await user.click(screen.getByRole('button', { name: 'submit' }));
    expect(submitMutate).not.toHaveBeenCalled();
    expect(screen.getByRole('textbox', { name: /why vegan/ })).toHaveAttribute(
      'aria-invalid',
      'true',
    );
  });

  it('drops answers to questions hidden by a later change', async () => {
    const user = userEvent.setup();
    renderScreen();
    await user.click(screen.getByRole('radio', { name: 'vegan' }));
    await user.type(screen.getByRole('textbox', { name: /why vegan/ }), 'ethics');
    await user.click(screen.getByRole('radio', { name: 'veg' }));
    await user.click(screen.getByRole('button', { name: 'submit' }));
    expect(submitMutate).toHaveBeenCalledWith({ diet: 'veg' });
  });
});
