import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ReserveTable } from './ReserveTable';

describe('ReserveTable', () => {
  it('renders a row per source plus the total', () => {
    render(<ReserveTable />);

    const spicyMoon = screen.getByText('5/9 spicy moon brunch').closest('tr')!;
    expect(within(spicyMoon).getByText('−$39.64')).toBeInTheDocument();

    const total = screen.getByText('total').closest('tr')!;
    expect(within(total).getByText('$34.25')).toBeInTheDocument();
    expect(within(total).getByText('+$132.49')).toBeInTheDocument();
  });

  it('explains where leftover comes from', () => {
    render(<ReserveTable />);

    expect(screen.getByText(/no-show or cancel late/)).toBeInTheDocument();
  });
});
