import { screen } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';

import SurveyThanksScreen from './SurveyThanksScreen';

vi.mock('@/api/surveys', () => ({
  useSurvey: () => ({
    isPending: false,
    data: { confirmationMessage: 'thanks!', myResponseId: 'r1' },
  }),
}));

function renderScreen() {
  renderWithProviders(
    <Routes>
      <Route path="/surveys/:slug/thanks" element={<SurveyThanksScreen />} />
    </Routes>,
    { route: '/surveys/feedback/thanks' },
  );
}

describe('SurveyThanksScreen', () => {
  it('styles the edit and home links as buttons', () => {
    renderScreen();
    const edit = screen.getByRole('link', { name: 'edit your response' });
    expect(edit).toHaveAttribute('href', '/surveys/feedback');
    expect(edit).toHaveClass('border-border-strong');
    expect(screen.getByRole('link', { name: 'back to home' })).toHaveClass('bg-brand-600');
  });

  it('scrolls to the top so the message is in view after submitting from far down', () => {
    const scrollTo = vi.spyOn(window, 'scrollTo');
    renderScreen();
    expect(scrollTo).toHaveBeenCalledWith(0, 0);
  });
});
