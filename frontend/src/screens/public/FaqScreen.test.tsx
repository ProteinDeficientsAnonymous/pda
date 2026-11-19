import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useFaq } from '@/api/content';
import { setAuthed, setUnauthed } from '@/test/auth';
import { makeUser } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import FaqScreen from './FaqScreen';

vi.mock('@/api/content', () => ({
  useFaq: vi.fn(),
  useUpdateFaq: vi.fn(() => ({ mutateAsync: vi.fn() })),
}));

vi.mock('@/components/RichEditor/RichEditor', () => ({
  RichEditor: () => <div data-testid="rich-editor" />,
}));

const mockUseFaq = vi.mocked(useFaq);

const baseFaqData = {
  content: '',
  contentPm: '',
  contentHtml: '<p>Frequently asked questions</p>',
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

describe('FaqScreen', () => {
  it('shows loading indicator while fetching', () => {
    mockUseFaq.mockReturnValue({
      isPending: true,
      isError: false,
      data: undefined,
    } as ReturnType<typeof useFaq>);

    renderWithProviders(<FaqScreen />);

    expect(screen.getByText('loading…')).toBeInTheDocument();
  });

  it('hides edit button for member without edit_faq permission', () => {
    const memberUser = {
      ...baseUser,
      roles: [{ id: 'role-1', name: 'member', isDefault: true, permissions: [] }],
    };
    setAuthed(memberUser, 'token');
    mockUseFaq.mockReturnValue({
      isPending: false,
      isError: false,
      data: baseFaqData,
    } as ReturnType<typeof useFaq>);

    renderWithProviders(<FaqScreen />);

    expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument();
  });

  it('shows edit button for user with edit_faq permission', () => {
    const editorUser = {
      ...baseUser,
      roles: [{ id: 'role-1', name: 'faq-editor', isDefault: true, permissions: ['edit_faq'] }],
    };
    setAuthed(editorUser, 'token');
    mockUseFaq.mockReturnValue({
      isPending: false,
      isError: false,
      data: baseFaqData,
    } as ReturnType<typeof useFaq>);

    renderWithProviders(<FaqScreen />);

    expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument();
  });
});
