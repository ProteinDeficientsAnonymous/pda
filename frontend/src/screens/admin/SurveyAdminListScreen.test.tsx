import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import type { SurveySummary } from '@/api/surveyAdmin';

import SurveyAdminListScreen from './SurveyAdminListScreen';

const toastSuccess = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    success: (m: string) => {
      toastSuccess(m);
    },
    error: vi.fn(),
  },
}));

const surveys: SurveySummary[] = [
  {
    id: 's1',
    title: 'spring potluck',
    slug: 'spring-potluck',
    visibility: 'members_only',
    isActive: true,
    linkedEventId: null,
    createdAt: '2026-03-01T00:00:00Z',
    responseCount: 2,
  },
  {
    id: 's2',
    title: 'summer picnic',
    slug: 'summer-picnic',
    visibility: 'public',
    isActive: false,
    linkedEventId: null,
    createdAt: '2026-04-01T00:00:00Z',
    responseCount: 0,
  },
];

vi.mock('@/api/surveyAdmin', () => ({
  useAdminSurveys: () => ({ data: surveys, isPending: false, isError: false }),
  useCreateSurvey: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteSurvey: () => ({ mutate: vi.fn() }),
}));

describe('SurveyAdminListScreen', () => {
  it('copies the participant link for the clicked row', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });

    render(
      <MemoryRouter>
        <SurveyAdminListScreen />
      </MemoryRouter>,
    );

    expect(screen.getAllByRole('button', { name: 'copy link' })).toHaveLength(2);

    const row = screen.getByText('summer picnic').closest('article');
    if (!row) throw new Error('row not found');
    fireEvent.click(within(row).getByRole('button', { name: 'copy link' }));

    await vi.waitFor(() => {
      expect(toastSuccess).toHaveBeenCalledWith('link copied');
    });
    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/surveys/summer-picnic`);
  });
});
