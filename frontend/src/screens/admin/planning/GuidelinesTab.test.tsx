import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Permission } from '@/models/permissions';
import { setAuthed } from '@/test/auth';
import { makeUserWithPermissions } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import { GuidelinesTab } from './GuidelinesTab';

let checklist: { isPending: boolean; isError: boolean; data?: unknown[] };

vi.mock('@/api/planningChecklist', () => ({
  PLANNING_GUIDELINES_SLUG: 'planning-guidelines',
  useChecklist: () => checklist,
}));

vi.mock('./ChecklistEditor', () => ({
  ChecklistEditor: () => <div>checklist editor</div>,
}));

vi.mock('@/api/content', () => ({
  useEditablePage: () => ({
    isPending: false,
    isError: false,
    data: { contentHtml: '<h2>hosting</h2><ul><li>arrive early!</li></ul>', contentPm: '{}' },
  }),
  useUpdateEditablePage: () => ({ mutateAsync: vi.fn() }),
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
  setAuthed(makeUserWithPermissions([Permission.ViewEventPlanning]));
});

describe('GuidelinesTab', () => {
  it('shows the checklist in order with details, then the guidelines', () => {
    renderWithProviders(<GuidelinesTab />);
    const items = screen.getAllByRole('listitem');
    expect(items[0]).toHaveTextContent('secure venue');
    expect(items[1]).toHaveTextContent('add the questionnaireall are required');
    expect(screen.getByText('arrive early!')).toBeInTheDocument();
  });

  it('only lets coordinators edit the guidelines and checklist', () => {
    const { unmount } = renderWithProviders(<GuidelinesTab />);
    expect(screen.queryByRole('button', { name: 'edit' })).not.toBeInTheDocument();
    expect(screen.queryByText('checklist editor')).not.toBeInTheDocument();
    unmount();
    setAuthed(makeUserWithPermissions([Permission.ManageEventPlanning]));
    renderWithProviders(<GuidelinesTab />);
    expect(screen.getByRole('button', { name: 'edit' })).toBeInTheDocument();
    expect(screen.getByText('checklist editor')).toBeInTheDocument();
  });

  it('shows an empty state and a load error', () => {
    checklist = { isPending: false, isError: false, data: [] };
    const { unmount } = renderWithProviders(<GuidelinesTab />);
    expect(screen.getByText('no checklist items yet 🌿')).toBeInTheDocument();
    unmount();
    checklist = { isPending: false, isError: true };
    renderWithProviders(<GuidelinesTab />);
    expect(screen.getByText("couldn't load the checklist — try refreshing")).toBeInTheDocument();
  });
});
