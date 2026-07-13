import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Footer } from './Footer';

describe('Footer', () => {
  it('renders a lowercase copyright line with the current year', () => {
    const year = new Date().getFullYear();
    render(<Footer />);

    const footer = screen.getByRole('contentinfo');
    expect(footer).toHaveTextContent(`© ${year} protein deficients anonymous`);
  });
});
