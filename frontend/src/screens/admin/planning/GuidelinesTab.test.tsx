import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Permission } from '@/models/permissions';
import { setAuthed } from '@/test/auth';
import { makeUserWithPermissions } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import { GuidelinesTab } from './GuidelinesTab';

const update = vi.fn();
let page: {
  isPending: boolean;
  isError: boolean;
  data?: { contentHtml: string; contentPm: string };
};
let savedWith: ((pm: string) => Promise<void>) | undefined;

vi.mock('@/api/planningChecklist', () => ({ PLANNING_GUIDELINES_SLUG: 'planning-guidelines' }));

vi.mock('@/api/content', () => ({
  useEditablePage: () => page,
  useUpdateEditablePage: () => ({ mutateAsync: update }),
}));

vi.mock('@/components/EditableHtmlBlock', () => ({
  EditableHtmlBlock: ({
    canEdit,
    contentHtml,
    onSave,
  }: {
    canEdit: boolean;
    contentHtml: string;
    onSave: (pm: string) => Promise<void>;
  }) => {
    savedWith = onSave;
    return <div>{`${contentHtml}${canEdit ? ' (editable)' : ''}`}</div>;
  },
}));

beforeEach(() => {
  page = {
    isPending: false,
    isError: false,
    data: { contentHtml: 'arrive early!', contentPm: '{}' },
  };
  update.mockReset().mockResolvedValue({});
  savedWith = undefined;
  setAuthed(makeUserWithPermissions([Permission.ViewEventPlanning]));
});

describe('GuidelinesTab', () => {
  it('shows the guidelines read-only to planners', () => {
    renderWithProviders(<GuidelinesTab />);
    expect(screen.getByText('arrive early!')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'event protocol' })).toHaveAttribute(
      'href',
      '/event-protocol',
    );
  });

  it('lets coordinators edit and saves the new content', async () => {
    setAuthed(makeUserWithPermissions([Permission.ManageEventPlanning]));
    renderWithProviders(<GuidelinesTab />);
    expect(screen.getByText('arrive early! (editable)')).toBeInTheDocument();
    await savedWith?.('{"type":"doc"}');
    expect(update).toHaveBeenCalledWith({ contentPm: '{"type":"doc"}' });
  });

  it('shows loading until the page arrives', () => {
    page = { isPending: true, isError: false };
    renderWithProviders(<GuidelinesTab />);
    expect(screen.getByText('loading…')).toBeInTheDocument();
  });

  it('shows a load error when there is no content', () => {
    page = { isPending: false, isError: true };
    renderWithProviders(<GuidelinesTab />);
    expect(screen.getByText("couldn't load the guidelines — try refreshing")).toBeInTheDocument();
  });

  it('keeps showing loaded guidelines when a refetch fails', () => {
    page = { ...page, isError: true };
    renderWithProviders(<GuidelinesTab />);
    expect(screen.getByText('arrive early!')).toBeInTheDocument();
    expect(
      screen.queryByText("couldn't load the guidelines — try refreshing"),
    ).not.toBeInTheDocument();
  });
});
