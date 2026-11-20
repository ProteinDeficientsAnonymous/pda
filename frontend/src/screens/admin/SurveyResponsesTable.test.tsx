import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { Survey, SurveyResponseAdmin } from '@/api/surveyAdmin';

import { SurveyResponsesTable } from './SurveyResponsesTable';

const survey = {
  id: 'srv-1',
  anonymous: false,
  feedbackEventType: '',
  questions: [{ id: 'q-notes', label: 'notes', fieldType: 'text', options: [] }],
} as unknown as Survey;

const response = {
  id: 'r-1',
  userName: 'ada',
  answers: { 'q-notes': { label: 'notes', answer: `https://example.com/${'x'.repeat(150)}` } },
  submittedAt: '2026-04-20T12:00:00.000Z',
} as unknown as SurveyResponseAdmin;

describe('SurveyResponsesTable', () => {
  it('should keep the absolute sr-only header inside its own scroll container', () => {
    render(<SurveyResponsesTable survey={survey} responses={[response]} onDelete={vi.fn()} />);
    const scroller = screen.getByRole('table').parentElement;
    expect(scroller).toHaveClass('overflow-x-auto', 'relative');
    expect(scroller).toContainElement(screen.getByText('actions'));
  });

  it('should let long unbroken answers wrap inside their column', () => {
    render(<SurveyResponsesTable survey={survey} responses={[response]} onDelete={vi.fn()} />);
    expect(screen.getByText(/^https:\/\/example\.com\/x+$/)).toHaveClass('break-words');
  });

  it('should show answers to removed questions under their stored label', () => {
    const withRemoved = {
      ...response,
      answers: { ...response.answers, 'q-gone': { label: 'anyone to shout out?', answer: 'sam!' } },
    } as SurveyResponseAdmin;
    render(<SurveyResponsesTable survey={survey} responses={[withRemoved]} onDelete={vi.fn()} />);
    expect(
      screen.getByRole('columnheader', { name: 'anyone to shout out? (removed)' }),
    ).toBeVisible();
    expect(screen.getByText('sam!')).toBeVisible();
  });
});
