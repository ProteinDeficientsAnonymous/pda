import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useHome } from '@/api/content';
import { setAuthed, setUnauthed } from '@/test/auth';
import { makeUser } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import HomeScreen from './HomeScreen';

// Mock API before importing the screen
vi.mock('@/api/content', () => ({
  useHome: vi.fn(),
  useUpdateHome: vi.fn(() => ({ mutateAsync: vi.fn() })),
}));

// Mock the RichEditor — TipTap requires a DOM environment not available in jsdom
vi.mock('@/components/RichEditor/RichEditor', () => ({
  RichEditor: () => <div data-testid="rich-editor" />,
}));

const mockUseHome = vi.mocked(useHome);

const baseHomeData = {
  content: '',
  contentPm: '',
  contentHtml: '<p>Welcome</p>',
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

describe('HomeScreen', () => {
  it('shows loading indicator while data is fetching', () => {
    mockUseHome.mockReturnValue({
      isPending: true,
      isError: false,
      data: undefined,
    } as ReturnType<typeof useHome>);

    renderWithProviders(<HomeScreen />);

    expect(screen.getByText('loading…')).toBeInTheDocument();
  });

  it('shows edit button for user with edit_homepage permission', () => {
    const editorUser = {
      ...baseUser,
      roles: [
        {
          id: 'role-1',
          name: 'editor',
          isDefault: true,
          permissions: ['edit_homepage'],
        },
      ],
    };
    setAuthed(editorUser, 'token');
    mockUseHome.mockReturnValue({
      isPending: false,
      isError: false,
      data: baseHomeData,
    } as ReturnType<typeof useHome>);

    renderWithProviders(<HomeScreen />);

    expect(screen.getAllByRole('button', { name: /edit/i }).length).toBeGreaterThan(0);
  });
});
