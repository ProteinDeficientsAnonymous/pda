import { describe, it, expect } from 'vitest';
import { buildWhatsAppHref, renderWelcomeMessage } from './welcomeMessage';

describe('renderWelcomeMessage', () => {
  it('substitutes all three placeholders', () => {
    const out = renderWelcomeMessage('hi ${NAME}, this is ${SENDER_NAME}, sign in: ${MAGIC_LINK}', {
      name: 'Sam',
      senderName: 'Vetter',
      magicLink: 'https://pda.test/m/abc',
    });
    expect(out).toBe('hi Sam, this is Vetter, sign in: https://pda.test/m/abc');
  });

  it('replaces every occurrence of a repeated placeholder', () => {
    const out = renderWelcomeMessage('${NAME} ${NAME}!', {
      name: 'Sam',
      senderName: '',
      magicLink: '',
    });
    expect(out).toBe('Sam Sam!');
  });

  it('leaves unrelated text and unknown placeholders alone', () => {
    const out = renderWelcomeMessage('${NAME} — ${UNKNOWN}', {
      name: 'Sam',
      senderName: '',
      magicLink: '',
    });
    expect(out).toBe('Sam — ${UNKNOWN}');
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
