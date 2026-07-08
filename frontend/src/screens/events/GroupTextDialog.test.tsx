import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { TextRecipients } from '@/api/textRecipients';

const toastSuccess = vi.fn();
const toastError = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    success: (m: string) => {
      toastSuccess(m);
    },
    error: (m: string) => {
      toastError(m);
    },
  },
}));

interface RecipientsQueryResult {
  data: TextRecipients | undefined;
  isPending: boolean;
  isError: boolean;
}
const useTextRecipients = vi.fn<() => RecipientsQueryResult>();
vi.mock('@/api/textRecipients', () => ({
  useTextRecipients: () => useTextRecipients(),
}));

import { GroupTextDialog } from './GroupTextDialog';

function recipients(overrides: Partial<TextRecipients> = {}): TextRecipients {
  return {
    attending: ['+15551112222'],
    maybe: ['+15559990000'],
    cantGo: ['+15553334444'],
    waitlisted: [],
    invited: [],
    ...overrides,
  };
}

function mockLoaded(data: TextRecipients) {
  useTextRecipients.mockReturnValue({ data, isPending: false, isError: false });
}

const noop = () => {};
const originalUserAgent = navigator.userAgent;

beforeEach(() => {
  toastSuccess.mockClear();
  toastError.mockClear();
  useTextRecipients.mockReset();
  // Pin an Apple UA so buildSmsUri emits the /open?addresses= form.
  Object.defineProperty(navigator, 'userAgent', {
    value: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    configurable: true,
  });
});

afterEach(() => {
  Object.defineProperty(navigator, 'userAgent', { value: originalUserAgent, configurable: true });
  vi.restoreAllMocks();
});

describe('GroupTextDialog', () => {
  it('shows a loading state while recipients load', () => {
    useTextRecipients.mockReturnValue({ data: undefined, isPending: true, isError: false });
    render(<GroupTextDialog eventId="e1" open onClose={noop} />);
    expect(screen.getByText(/loading numbers/i)).toBeInTheDocument();
  });

  it('shows an error state when the fetch fails', () => {
    useTextRecipients.mockReturnValue({ data: undefined, isPending: false, isError: true });
    render(<GroupTextDialog eventId="e1" open onClose={noop} />);
    expect(screen.getByText(/couldn't load numbers/i)).toBeInTheDocument();
  });

  it('defaults to going + maybe selected', () => {
    mockLoaded(recipients());
    render(<GroupTextDialog eventId="e1" open onClose={noop} />);
    const pressed = screen.getAllByRole('button', { pressed: true }).map((el) => el.textContent);
    expect(pressed).toEqual(['going1', 'maybe1']);
    expect(screen.getAllByRole('button', { pressed: false }).map((el) => el.textContent)).toContain(
      "can't go1",
    );
  });

  it('renders an sms: group-draft link (Apple /open?addresses= form) for the selected groups', () => {
    mockLoaded(recipients());
    render(<GroupTextDialog eventId="e1" open onClose={noop} />);
    const link = screen.getByRole('link', { name: /text them/i });
    expect(link).toHaveAttribute('href', 'sms:/open?addresses=+15551112222,+15559990000');
  });

  it('updates the sms: link when a group is toggled', () => {
    mockLoaded(recipients());
    render(<GroupTextDialog eventId="e1" open onClose={noop} />);
    fireEvent.click(screen.getByRole('button', { name: /^maybe/i }));
    fireEvent.click(screen.getByRole('button', { name: /can't go/i }));
    const link = screen.getByRole('link', { name: /text them/i });
    expect(link).toHaveAttribute('href', 'sms:/open?addresses=+15551112222,+15553334444');
  });

  it('copies numbers via the secondary copy action and closes', async () => {
    mockLoaded(recipients());
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
    const onClose = vi.fn();

    render(<GroupTextDialog eventId="e1" open onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: /copy numbers instead/i }));
    await vi.waitFor(() => {
      expect(writeText).toHaveBeenCalledWith('+15551112222, +15559990000');
    });
    expect(onClose).toHaveBeenCalled();
  });

  it('does not offer a group with no textable people', () => {
    mockLoaded(recipients({ maybe: [], cantGo: [] }));
    render(<GroupTextDialog eventId="e1" open onClose={noop} />);
    expect(screen.queryByRole('button', { name: /^maybe/i })).toBeNull();
    expect(screen.queryByRole('button', { name: /invited/i })).toBeNull();
  });

  it('offers the invited group when invited phones are present', () => {
    mockLoaded(recipients({ invited: ['+15558887777'] }));
    render(<GroupTextDialog eventId="e1" open onClose={noop} />);
    expect(screen.getByRole('button', { name: /invited/i })).toBeInTheDocument();
  });

  it('shows an empty state when no group has a number', () => {
    mockLoaded(recipients({ attending: [], maybe: [], cantGo: [], waitlisted: [], invited: [] }));
    render(<GroupTextDialog eventId="e1" open onClose={noop} />);
    expect(screen.getByText(/no one has a number/i)).toBeInTheDocument();
  });
});
