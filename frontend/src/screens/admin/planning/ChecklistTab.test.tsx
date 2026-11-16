import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Permission } from '@/models/permissions';
import { setAuthed } from '@/test/auth';
import { makeUserWithPermissions } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import { ChecklistTab } from './ChecklistTab';

let checklist: { isPending: boolean; isError: boolean; data?: unknown[] };

vi.mock('@/api/planningChecklist', () => ({
  useChecklist: () => checklist,
}));

vi.mock('./ChecklistEditor', () => ({
  ChecklistEditor: () => <div>checklist editor</div>,
}));

beforeEach(() => {
  setAuthed(makeUserWithPermissions([Permission.ViewEventPlanning]));
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

  it('gives coordinators the editor instead of the plain list', () => {
    setAuthed(makeUserWithPermissions([Permission.ManageEventPlanning]));
    renderWithProviders(<ChecklistTab />);
    expect(screen.getByText('checklist editor')).toBeInTheDocument();
    expect(screen.queryByRole('listitem')).not.toBeInTheDocument();
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
