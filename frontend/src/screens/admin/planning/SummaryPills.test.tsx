import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { SummaryPills } from './SummaryPills';

describe('SummaryPills', () => {
  it('renders each count with its label', () => {
    render(<SummaryPills counts={{ needPlanner: 6, waiting: 5, noForm: 2 }} />);
    expect(screen.getByText('need a planner').parentElement).toHaveTextContent('6 need a planner');
    expect(screen.getByText('waiting').parentElement).toHaveTextContent('5 waiting');
    expect(screen.getByText('no form').parentElement).toHaveTextContent('2 no form');
    expect(screen.getByText('6')).toHaveClass('font-semibold');
  });

  it('still renders a zero count', () => {
    render(<SummaryPills counts={{ needPlanner: 1, waiting: 0, noForm: 0 }} />);
    expect(screen.getByText('waiting').parentElement).toHaveTextContent('0 waiting');
  });
});
