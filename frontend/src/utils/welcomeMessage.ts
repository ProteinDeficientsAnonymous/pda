export function buildMagicLinkUrl(token: string): string {
  return `${window.location.origin}/magic-login/${token}`;
}

// Legacy hardcoded body — still used by member-create / bulk-create /
// member-detail flows. The join-request approval flow uses the editable
// template via renderWelcomeMessage instead.
export function buildWelcomeMessage(displayName: string | null | undefined, url: string): string {
  const name = (displayName ?? '').trim();
  const greeting = name ? `hi ${name} 🌱` : 'hi 🌱';
  return `${greeting} welcome to pda! use this link to sign in: ${url}`;
}

export interface WelcomeMessageVars {
  name: string;
  senderName: string;
  magicLink: string;
}

export function renderWelcomeMessage(template: string, vars: WelcomeMessageVars): string {
  return template
    .replaceAll('${NAME}', vars.name)
    .replaceAll('${SENDER_NAME}', vars.senderName)
    .replaceAll('${MAGIC_LINK}', vars.magicLink);
}

export function buildSmsHref(phoneNumber: string, body: string): string {
  return `sms:${phoneNumber}?body=${encodeURIComponent(body)}`;
}

// wa.me deeplink — works with personal WhatsApp; no business API needed.
// Phone must be digits-only (E.164 minus the `+`).
export function buildWhatsAppHref(phoneNumber: string, body: string): string {
  const digits = phoneNumber.replace(/\D/g, '');
  return `https://wa.me/${digits}?text=${encodeURIComponent(body)}`;
}
