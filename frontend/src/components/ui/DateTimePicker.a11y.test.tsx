import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { DateTimePicker } from './DateTimePicker';

describe('DateTimePicker accessibility', () => {
  it('renders a visible label and a discoverable trigger button with no axe violations', async () => {
    const { container } = render(<DateTimePicker label="starts" value={null} onChange={vi.fn()} />);

    expect(screen.getByText('starts')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /pick a date & time/i })).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('time input has an associated label when popover is open', async () => {
    const user = userEvent.setup();
    render(<DateTimePicker label="starts" value={null} onChange={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: /pick a date & time/i }));

    const timeInput = screen.getByLabelText(/^time$/i);
    expect(timeInput).toBeInTheDocument();
    expect(timeInput.tagName).toBe('INPUT');
  });
});
