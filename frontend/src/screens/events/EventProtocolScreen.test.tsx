import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Code } from '@/api/validationCodes';
import { Permission } from '@/models/permissions';
import { apiError } from '@/test/apiError';
import { setAuthed } from '@/test/auth';
import { makeUserWithPermissions } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import EventProtocolScreen from './EventProtocolScreen';

const update = vi.fn();
let page: { isPending: boolean; error: unknown; data?: { contentHtml: string; contentPm: string } };
let savedWith: ((pm: string) => Promise<void>) | undefined;

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
  page = { isPending: false, error: null, data: { contentHtml: 'bring signs', contentPm: '{}' } };
  update.mockReset().mockResolvedValue({});
  savedWith = undefined;
  setAuthed(makeUserWithPermissions([]));
});

describe('EventProtocolScreen', () => {
  it('shows the protocol read-only to members', () => {
    renderWithProviders(<EventProtocolScreen />);
    expect(screen.getByRole('heading', { name: 'event protocol' })).toBeInTheDocument();
    expect(screen.getByText('bring signs')).toBeInTheDocument();
  });

  it('lets planning managers edit and saves the new content', async () => {
    setAuthed(makeUserWithPermissions([Permission.ManageEventPlanning]));
    renderWithProviders(<EventProtocolScreen />);
    expect(screen.getByText('bring signs (editable)')).toBeInTheDocument();
    await savedWith?.('{"type":"doc"}');
    expect(update).toHaveBeenCalledWith({ contentPm: '{"type":"doc"}' });
  });

  it('says members only on a 403', () => {
    page = { isPending: false, error: apiError(403, Code.Page.MembersOnly) };
    renderWithProviders(<EventProtocolScreen />);
    expect(screen.getByText('this page is for members only')).toBeInTheDocument();
  });

  it('shows a load error otherwise', () => {
    page = { isPending: false, error: new Error('boom') };
    renderWithProviders(<EventProtocolScreen />);
    expect(
      screen.getByText("couldn't load the event protocol — try refreshing"),
    ).toBeInTheDocument();
  });
});
