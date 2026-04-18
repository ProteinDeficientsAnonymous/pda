import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { HtmlContent } from './HtmlContent';

describe('HtmlContent', () => {
  it('renders allowed markup', () => {
    const { container } = render(<HtmlContent html="<p>hello <strong>world</strong></p>" />);
    expect(container.querySelector('strong')?.textContent).toBe('world');
  });

  it('strips script tags', () => {
    const { container } = render(<HtmlContent html='<p>ok</p><script>alert("x")</script>' />);
    expect(container.querySelector('script')).toBeNull();
    expect(container.textContent).toContain('ok');
  });

  it('strips inline event handlers', () => {
    const { container } = render(<HtmlContent html='<a href="#" onclick="alert(1)">click</a>' />);
    const anchor = container.querySelector('a');
    expect(anchor).not.toBeNull();
    expect(anchor?.getAttribute('onclick')).toBeNull();
  });

  it('strips javascript: URLs', () => {
    const { container } = render(<HtmlContent html='<a href="javascript:alert(1)">x</a>' />);
    const anchor = container.querySelector('a');
    // DOMPurify drops the unsafe href attribute entirely rather than rewriting it.
    const href = anchor?.getAttribute('href') ?? '';
    expect(href).not.toMatch(/^javascript:/i);
  });

  it('strips iframes', () => {
    const { container } = render(
      <HtmlContent html='<p>a</p><iframe src="https://evil.example"></iframe>' />,
    );
    expect(container.querySelector('iframe')).toBeNull();
  });
});
