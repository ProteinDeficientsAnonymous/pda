import { afterEach, describe, expect, it, vi } from 'vitest';

import { addHeadingAnchors, scrollToHash, slugify } from './headingAnchors';

function parse(html: string): DocumentFragment {
  const template = document.createElement('template');
  template.innerHTML = addHeadingAnchors(html);
  return template.content;
}

describe('slugify', () => {
  it('lowercases and hyphenates', () => {
    expect(slugify('Do I have to be vegan to join?')).toBe('do-i-have-to-be-vegan-to-join');
  });

  it('strips accents and edge punctuation', () => {
    expect(slugify('  ¿Qué pasa — café?  ')).toBe('que-pasa-cafe');
  });
});

describe('addHeadingAnchors', () => {
  it('gives h1-h3 an id and a self-link', () => {
    const doc = parse('<h2>Do I have to be vegan?</h2><p>yes</p>');
    const heading = doc.querySelector('h2');
    expect(heading?.id).toBe('do-i-have-to-be-vegan');
    const anchor = heading?.querySelector('a.heading-anchor');
    expect(anchor?.getAttribute('href')).toBe('#do-i-have-to-be-vegan');
    expect(anchor?.getAttribute('aria-label')).toBe('link to this section');
  });

  it('dedupes repeated headings', () => {
    const ids = [
      ...parse('<h2>dues</h2><h3>dues</h3><h2>dues</h2>').querySelectorAll('h2, h3'),
    ].map((h) => h.id);
    expect(ids).toEqual(['dues', 'dues-2', 'dues-3']);
  });

  it('falls back when a heading has no slug-able text', () => {
    expect(parse('<h2>🌱</h2>').querySelector('h2')?.id).toBe('section');
  });

  it('leaves non-heading content alone', () => {
    const html = '<p>hi <strong>there</strong></p>';
    expect(addHeadingAnchors(html)).toBe(html);
  });
});

describe('scrollToHash', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('scrolls the matching element into view', () => {
    document.body.innerHTML = '<h2 id="dues">dues</h2>';
    const target = document.getElementById('dues');
    if (!target) throw new Error('missing target');
    target.scrollIntoView = vi.fn();
    scrollToHash('#dues');
    expect(target.scrollIntoView).toHaveBeenCalled();
  });

  it('ignores an empty or unknown hash', () => {
    expect(() => {
      scrollToHash('');
      scrollToHash('#nope');
    }).not.toThrow();
  });
});
