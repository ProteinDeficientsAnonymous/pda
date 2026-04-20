export function buildMagicLinkUrl(token: string): string {
  return `${window.location.origin}/magic-login/${token}`;
}

export function buildWelcomeMessage(displayName: string | null | undefined, url: string): string {
  const name = (displayName ?? '').trim();
  const greeting = name ? `hi ${name} 🌱` : 'hi 🌱';
  return `${greeting} welcome to pda! use this link to sign in: ${url}`;
}

export function buildSmsHref(phoneNumber: string, body: string): string {
  return `sms:${phoneNumber}?body=${encodeURIComponent(body)}`;
}
