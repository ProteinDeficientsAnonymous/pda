import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { NotificationType } from '@/models/notification';

vi.mock('@/api/notifications', () => ({
  useNotificationHistory: vi.fn(),
  useMarkNotificationRead: vi.fn(),
}));

vi.mock('@/utils/errorReporter', () => ({
  reportError: vi.fn().mockResolvedValue(undefined),
}));

import { useMarkNotificationRead, useNotificationHistory } from '@/api/notifications';

import NotificationsScreen from './NotificationsScreen';

const mockUseHistory = vi.mocked(useNotificationHistory);
const mockUseMarkRead = vi.mocked(useMarkNotificationRead);

function makeNotification(id: string, message: string, isRead = false) {
  return {
    id,
    notificationType: NotificationType.EventInvite,
    eventId: 'evt1',
    relatedUserId: null,
    message,
    isRead,
    createdAt: '2024-01-01T00:00:00Z',
  };
}

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={['/notifications']}>
      <NotificationsScreen />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockUseMarkRead.mockReturnValue({
    mutate: vi.fn(),
  } as unknown as ReturnType<typeof useMarkNotificationRead>);
});

describe('NotificationsScreen', () => {
  it('shows a loading state while pending', () => {
    mockUseHistory.mockReturnValue({
      isPending: true,
      isError: false,
    } as unknown as ReturnType<typeof useNotificationHistory>);
    renderScreen();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('shows an error state on failure', () => {
    mockUseHistory.mockReturnValue({
      isPending: false,
      isError: true,
    } as unknown as ReturnType<typeof useNotificationHistory>);
    renderScreen();
    expect(screen.getByRole('alert')).toHaveTextContent(/couldn't load notifications/i);
  });

  it('shows an empty state when there are no notifications', () => {
    mockUseHistory.mockReturnValue({
      isPending: false,
      isError: false,
      data: { pages: [[]], pageParams: [0] },
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: vi.fn(),
    } as unknown as ReturnType<typeof useNotificationHistory>);
    renderScreen();
    expect(screen.getByText(/nothing here yet/i)).toBeInTheDocument();
  });

  it('flattens all pages into a single list', () => {
    mockUseHistory.mockReturnValue({
      isPending: false,
      isError: false,
      data: {
        pages: [[makeNotification('a', 'first invite')], [makeNotification('b', 'second invite')]],
        pageParams: [0, 30],
      },
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: vi.fn(),
    } as unknown as ReturnType<typeof useNotificationHistory>);
    renderScreen();
    expect(screen.getByText('first invite')).toBeInTheDocument();
    expect(screen.getByText('second invite')).toBeInTheDocument();
  });

  it('shows "load more" and fetches the next page on click', async () => {
    const user = userEvent.setup();
    const fetchNextPage = vi.fn();
    mockUseHistory.mockReturnValue({
      isPending: false,
      isError: false,
      data: { pages: [[makeNotification('a', 'invite')]], pageParams: [0] },
      hasNextPage: true,
      isFetchingNextPage: false,
      fetchNextPage,
    } as unknown as ReturnType<typeof useNotificationHistory>);
    renderScreen();

    await user.click(screen.getByRole('button', { name: /load more/i }));
    expect(fetchNextPage).toHaveBeenCalledTimes(1);
  });

  it('hides "load more" when there is no next page', () => {
    mockUseHistory.mockReturnValue({
      isPending: false,
      isError: false,
      data: { pages: [[makeNotification('a', 'invite')]], pageParams: [0] },
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: vi.fn(),
    } as unknown as ReturnType<typeof useNotificationHistory>);
    renderScreen();
    expect(screen.queryByRole('button', { name: /load more/i })).not.toBeInTheDocument();
  });
});
