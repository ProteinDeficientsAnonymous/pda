import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  buildRsvpLinkUrl,
  buildSmsHref,
  buildWelcomeMessage,
  buildWhatsAppHref,
  renderWelcomeMessage,
} from './welcomeMessage';

const IPHONE_UA =
  'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1';
const ANDROID_UA =
  'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36';

function setUserAgent(ua: string) {
  vi.spyOn(navigator, 'userAgent', 'get').mockReturnValue(ua);
}

describe('buildSmsHref', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('uses & separator on iOS so Messages opens a draft instead of showing the raw url', () => {
    setUserAgent(IPHONE_UA);
    const href = buildSmsHref('+15551234567', 'hi there');
    expect(href).toBe('sms:+15551234567&body=hi%20there');
  });

  it('uses ? separator on Android', () => {
    setUserAgent(ANDROID_UA);
    const href = buildSmsHref('+15551234567', 'hi there');
    expect(href).toBe('sms:+15551234567?body=hi%20there');
  });

  it('url-encodes the body (newlines, emoji, special chars)', () => {
    setUserAgent(ANDROID_UA);
    const href = buildSmsHref('+15551234567', 'hi 🌱\nlink: https://x/y?z=1');
    expect(href).toContain('body=hi%20%F0%9F%8C%B1%0Alink%3A%20https%3A%2F%2Fx%2Fy%3Fz%3D1');
  });
});

describe('buildWelcomeMessage', () => {
  it('greets by name when provided', () => {
    expect(buildWelcomeMessage('alex', 'https://x/y')).toBe(
      'hi alex 🌱 welcome to pda! use this link to sign in: https://x/y',
    );
  });

  it('falls back to a name-less greeting when display name is missing or blank', () => {
    expect(buildWelcomeMessage(null, 'https://x/y')).toBe(
      'hi 🌱 welcome to pda! use this link to sign in: https://x/y',
    );
    expect(buildWelcomeMessage('   ', 'https://x/y')).toBe(
      'hi 🌱 welcome to pda! use this link to sign in: https://x/y',
    );
  });
});

describe('renderWelcomeMessage', () => {
  it('substitutes all five placeholders', () => {
    const out = renderWelcomeMessage(
      'hi ${FIRST_NAME}, this is ${SENDER_NAME}, sign in: ${MAGIC_LINK}, rsvp: ${RSVP_LINK}, chat: ${WHATSAPP_LINK}',
      {
        name: 'Sam',
        senderName: 'Vetter',
        magicLink: 'https://pda.test/m/abc',
        rsvpLink: 'https://pda.test/my-rsvps?token=xyz',
        whatsappLink: 'https://chat.whatsapp.com/xyz',
      },
    );
    expect(out).toBe(
      'hi Sam, this is Vetter, sign in: https://pda.test/m/abc, rsvp: https://pda.test/my-rsvps?token=xyz, chat: https://chat.whatsapp.com/xyz',
    );
  });

  it('replaces every occurrence of a repeated placeholder', () => {
    const out = renderWelcomeMessage('${FIRST_NAME} ${FIRST_NAME}!', {
      name: 'Sam',
      senderName: '',
      magicLink: '',
      whatsappLink: '',
    });
    expect(out).toBe('Sam Sam!');
  });

  it('leaves unrelated text and unknown placeholders alone', () => {
    const out = renderWelcomeMessage('${FIRST_NAME} — ${UNKNOWN}', {
      name: 'Sam',
      senderName: '',
      magicLink: '',
      whatsappLink: '',
    });
    expect(out).toBe('Sam — ${UNKNOWN}');
  });

  it('renders ${FIRST_NAME} as the first name', () => {
    const out = renderWelcomeMessage('hi ${FIRST_NAME}!', {
      name: 'ada',
      senderName: 'sender',
      magicLink: 'http://x',
      whatsappLink: '',
    });
    expect(out).toBe('hi ada!');
  });

  it('leaves ${RSVP_LINK} empty when no rsvpLink is supplied', () => {
    const out = renderWelcomeMessage('x${RSVP_LINK}y', {
      name: 'ada',
      senderName: 'sender',
      whatsappLink: '',
    });
    expect(out).toBe('xy');
  });
});

describe('buildRsvpLinkUrl', () => {
  it('builds a /my-rsvps manage url from a token', () => {
    expect(buildRsvpLinkUrl('abc123')).toBe(`${window.location.origin}/my-rsvps?token=abc123`);
  });
});

describe('buildWhatsAppHref', () => {
  it('strips non-digits and url-encodes the body', () => {
    const href = buildWhatsAppHref('+1 (202) 555-1234', 'hi sam — sign in!');
    expect(href).toBe('https://wa.me/12025551234?text=hi%20sam%20%E2%80%94%20sign%20in!');
  });

  it('handles digits-only input', () => {
    const href = buildWhatsAppHref('12025551234', 'hi');
    expect(href).toBe('https://wa.me/12025551234?text=hi');
  });
});
