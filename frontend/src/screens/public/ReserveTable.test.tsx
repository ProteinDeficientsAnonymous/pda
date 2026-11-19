import { screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { type Reserve, useReserve } from '@/api/reserve';
import { renderWithProviders } from '@/test/render';

import { ReserveTable } from './ReserveTable';

vi.mock('@/api/reserve', () => ({ useReserve: vi.fn() }));

const mockUseReserve = vi.mocked(useReserve);

function withData(data: Reserve | undefined) {
  mockUseReserve.mockReturnValue({ data } as ReturnType<typeof useReserve>);
}

const entry = (id: string, label: string, leftOver: number, facilitatorDrinks = 0) => ({
  id,
  label,
  collected: 0,
  paidOut: 0,
  facilitatorDrinks,
  leftOver,
});

beforeEach(() => vi.clearAllMocks());

describe('ReserveTable', () => {
  it('renders a row per entry plus totals', () => {
    withData({
      entries: [
        entry('1', '4/25 donut walk', 74.03, 10.5),
        entry('2', '5/9 spicy moon brunch', -39.64),
      ],
      updatedAt: new Date(2026, 10, 15),
    });

    renderWithProviders(<ReserveTable />);

    const spicyMoon = screen.getByText('5/9 spicy moon brunch').closest('tr')!;
    expect(within(spicyMoon).getByText('−$39.64')).toBeInTheDocument();
    const total = screen.getByText('total').closest('tr')!;
    expect(within(total).getByText('$10.50')).toBeInTheDocument();
    expect(within(total).getByText('+$34.39')).toBeInTheDocument();
    expect(screen.getByText(/no-show or cancel late \(as of nov 15, 2026\)/)).toBeInTheDocument();
  });

  it('renders nothing when there are no entries', () => {
    withData({ entries: [], updatedAt: null });

    const { container } = renderWithProviders(<ReserveTable />);

    expect(container).toBeEmptyDOMElement();
  });
});
