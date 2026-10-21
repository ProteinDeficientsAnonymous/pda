import { describe, expect, it } from 'vitest';

import { cacheBustMediaUrl } from './mediaUrl';

describe('cacheBustMediaUrl', () => {
  it('should append ?v= when url is a relative /media/ path', () => {
    expect(cacheBustMediaUrl('/media/a.jpg', '2026-01-01T00:00:00Z')).toBe(
      '/media/a.jpg?v=2026-01-01T00%3A00%3A00Z',
    );
  });

  it('should leave absolute signed urls unchanged so query signatures stay valid', () => {
    const signed =
      'https://s3.example/bucket/a.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=abc';
    expect(cacheBustMediaUrl(signed, '2026-01-01T00:00:00Z')).toBe(signed);
  });

  it('should return the url when updatedAt is null', () => {
    expect(cacheBustMediaUrl('/media/a.jpg', null)).toBe('/media/a.jpg');
  });

  it('should return empty string when url is empty', () => {
    expect(cacheBustMediaUrl('', '2026-01-01T00:00:00Z')).toBe('');
  });
});
