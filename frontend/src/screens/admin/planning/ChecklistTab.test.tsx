import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';

import { ChecklistTab } from './ChecklistTab';

let checklist: { isPending: boolean; isError: boolean; data?: unknown[] };

vi.mock('@/api/planningChecklist', () => ({
  useChecklist: () => checklist,
}));

vi.mock('./ChecklistEditor', () => ({
  ChecklistEditor: ({ items }: { items: unknown[] }) => (
    <div>{`checklist editor with ${String(items.length)}`}</div>
  ),
}));

beforeEach(() => {
  checklist = {
    isPending: false,
    isError: false,
    data: [{ id: 'i1', text: 'secure venue', detail: '' }],
  };
});

describe('ChecklistTab', () => {
  it('gives coordinators the editor', () => {
    renderWithProviders(<ChecklistTab />);
    expect(screen.getByText('checklist editor with 1')).toBeInTheDocument();
    expect(screen.queryByText('no checklist items yet 🌿')).not.toBeInTheDocument();
  });

  it('shows loading until the checklist arrives', () => {
    checklist = { isPending: true, isError: false };
    renderWithProviders(<ChecklistTab />);
    expect(screen.getByText('loading…')).toBeInTheDocument();
  });

  it('shows an empty state above the add form', () => {
    checklist = { isPending: false, isError: false, data: [] };
    renderWithProviders(<ChecklistTab />);
    expect(screen.getByText('no checklist items yet 🌿')).toBeInTheDocument();
    expect(screen.getByText('checklist editor with 0')).toBeInTheDocument();
  });

  it('shows a load error', () => {
    checklist = { isPending: false, isError: true };
    renderWithProviders(<ChecklistTab />);
    expect(screen.getByText("couldn't load the checklist — try refreshing")).toBeInTheDocument();
  });
});
