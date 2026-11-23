const HEADING_SELECTOR = 'h1, h2, h3';

export function slugify(text: string): string {
  return text
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function uniqueSlug(base: string, used: Set<string>): string {
  let slug = base || 'section';
  for (let n = 2; used.has(slug); n += 1) slug = `${base || 'section'}-${String(n)}`;
  used.add(slug);
  return slug;
}

// Runs on already-sanitized html; ids are slugs of [a-z0-9-] so they can't carry markup.
export function addHeadingAnchors(html: string): string {
  const template = document.createElement('template');
  template.innerHTML = html;
  const used = new Set<string>();
  for (const heading of template.content.querySelectorAll(HEADING_SELECTOR)) {
    const slug = uniqueSlug(slugify(heading.textContent), used);
    heading.id = slug;
    const anchor = document.createElement('a');
    anchor.href = `#${slug}`;
    anchor.className = 'heading-anchor';
    anchor.setAttribute('aria-label', 'link to this section');
    anchor.textContent = '#';
    heading.append(anchor);
  }
  return template.innerHTML;
}

export function scrollToHash(hash: string): void {
  const id = decodeURIComponent(hash.replace(/^#/, ''));
  if (!id) return;
  document.getElementById(id)?.scrollIntoView();
}
