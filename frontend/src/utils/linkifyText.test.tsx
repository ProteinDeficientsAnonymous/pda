import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { linkifyText } from './linkifyText';

function renderText(text: string) {
  return render(<p>{linkifyText(text)}</p>);
}

describe('linkifyText', () => {
  it('returns the original text when no urls are present', () => {
    renderText('come hang out at the park');
    expect(screen.getByText('come hang out at the park')).toBeInTheDocument();
  });

  it('renders an https url as a clickable link', () => {
    renderText('rsvp at https://example.com soon');
    const link = screen.getByRole('link', { name: 'https://example.com' });
    expect(link).toHaveAttribute('href', 'https://example.com');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('prefixes www-only urls with https', () => {
    renderText('see www.example.com for details');
    const link = screen.getByRole('link', { name: 'www.example.com' });
    expect(link).toHaveAttribute('href', 'https://www.example.com');
  });

  it('strips trailing sentence punctuation from the link', () => {
    renderText('check https://example.com.');
    const link = screen.getByRole('link', { name: 'https://example.com' });
    expect(link).toHaveAttribute('href', 'https://example.com');
    expect(link.parentElement?.textContent).toBe('check https://example.com.');
  });

  it('renders multiple links in one string', () => {
    renderText('go to https://a.com or https://b.com');
    expect(screen.getByRole('link', { name: 'https://a.com' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'https://b.com' })).toBeInTheDocument();
  });
});
