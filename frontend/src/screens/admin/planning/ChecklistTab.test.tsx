import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';

import { ChecklistTab } from './ChecklistTab';

let checklist: { isPending: boolean; isError: boolean; data?: unknown[] };

vi.mock('@/api/planningChecklist', () => ({
  useChecklist: () => checklist,
}));

beforeEach(() => {
  checklist = {
    isPending: false,
    isError: false,
    data: [
      { id: 'i1', text: 'secure venue', detail: '' },
      { id: 'i2', text: 'add the questionnaire', detail: 'all are required' },
    ],
  };
});

describe('ChecklistTab', () => {
  it('shows the checklist in order with details', () => {
    renderWithProviders(<ChecklistTab />);
    const items = screen.getAllByRole('listitem');
    expect(items[0]).toHaveTextContent('secure venue');
    expect(items[1]).toHaveTextContent('add the questionnaireall are required');
  });

  it('shows loading until the checklist arrives', () => {
    checklist = { isPending: true, isError: false };
    renderWithProviders(<ChecklistTab />);
    expect(screen.getByText('loading…')).toBeInTheDocument();
  });

  it('shows an empty state', () => {
    checklist = { isPending: false, isError: false, data: [] };
    renderWithProviders(<ChecklistTab />);
    expect(screen.getByText('no checklist items yet 🌿')).toBeInTheDocument();
  });

  it('shows a load error', () => {
    checklist = { isPending: false, isError: true };
    renderWithProviders(<ChecklistTab />);
    expect(screen.getByText("couldn't load the checklist — try refreshing")).toBeInTheDocument();
  });
});
