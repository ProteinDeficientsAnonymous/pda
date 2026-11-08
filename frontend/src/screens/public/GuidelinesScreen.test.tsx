import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useGuidelines } from '@/api/content';
import { setAuthed, setUnauthed } from '@/test/auth';
import { makeUser } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import GuidelinesScreen from './GuidelinesScreen';

vi.mock('@/api/content', () => ({
  useGuidelines: vi.fn(),
  useUpdateGuidelines: vi.fn(() => ({ mutateAsync: vi.fn() })),
}));

vi.mock('@/components/RichEditor/RichEditor', () => ({
  RichEditor: () => <div data-testid="rich-editor" />,
}));

const mockUseGuidelines = vi.mocked(useGuidelines);

const baseGuidelinesData = {
  content: '',
  contentPm: '',
  contentHtml: '<p>Community guidelines content</p>',
  updatedAt: '2024-01-01T00:00:00Z',
};

const baseUser = makeUser({
  id: '1',
  phoneNumber: '+15551234567',
  email: 'test@example.com',
  weekStart: 'monday',
});

beforeEach(() => {
  vi.clearAllMocks();
  setUnauthed();
});

describe('GuidelinesScreen', () => {
  it('shows loading indicator while fetching', () => {
    mockUseGuidelines.mockReturnValue({
      isPending: true,
      isError: false,
      data: undefined,
    } as ReturnType<typeof useGuidelines>);

    renderWithProviders(<GuidelinesScreen />);

    expect(screen.getByText('loading…')).toBeInTheDocument();
  });

  it('hides edit button for member without edit_guidelines permission', () => {
    const memberUser = {
      ...baseUser,
      roles: [{ id: 'role-1', name: 'member', isDefault: true, permissions: [] }],
    };
    setAuthed(memberUser, 'token');
    mockUseGuidelines.mockReturnValue({
      isPending: false,
      isError: false,
      data: baseGuidelinesData,
    } as ReturnType<typeof useGuidelines>);

    renderWithProviders(<GuidelinesScreen />);

    expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument();
  });

  it('shows edit button for user with edit_guidelines permission', () => {
    const editorUser = {
      ...baseUser,
      roles: [
        {
          id: 'role-1',
          name: 'moderator',
          isDefault: true,
          permissions: ['edit_guidelines'],
        },
      ],
    };
    setAuthed(editorUser, 'token');
    mockUseGuidelines.mockReturnValue({
      isPending: false,
      isError: false,
      data: baseGuidelinesData,
    } as ReturnType<typeof useGuidelines>);

    renderWithProviders(<GuidelinesScreen />);

    expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument();
  });
});
