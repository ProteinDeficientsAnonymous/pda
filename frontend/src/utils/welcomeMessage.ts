import { formatEventDateTime } from './datetime';

export function buildMagicLinkUrl(token: string): string {
  return `${window.location.origin}/magic-login/${token}`;
}

// Legacy hardcoded body — still used by the member-detail flow. The join-request
// approval flow uses the editable template via renderWelcomeMessage instead.
export function buildWelcomeMessage(firstName: string | null | undefined, url: string): string {
  const name = (firstName ?? '').trim();
  const greeting = name ? `hi ${name} 🌱` : 'hi 🌱';
  return `${greeting} welcome to pda! use this link to sign in: ${url}`;
}

export interface WelcomeMessageVars {
  name: string;
  senderName: string;
  magicLink?: string;
  whatsappLink: string;
  nextOfficialEvent?: string;
  clubEvent?: string;
}

export interface MessageEvent {
  id: string;
  slug: string;
  title: string;
  startDatetime: Date;
}

export function formatSuggestedEvent(event: MessageEvent | null): string {
  if (!event) return '';
  const url = `${window.location.origin}/events/${event.slug || event.id}`;
  return `${event.title} — ${formatEventDateTime(event.startDatetime, null)}\n${url}`;
}

// No event drops the placeholder's whole paragraph, so the template's own lead-in goes with it.
function dropEmptyEventParagraphs(template: string, vars: WelcomeMessageVars): string {
  const empty = [
    !vars.nextOfficialEvent && '${NEXT_OFFICIAL_EVENT}',
    !vars.clubEvent && '${CLUB_EVENT}',
  ].filter((p): p is string => !!p && template.includes(p));
  if (empty.length === 0) return template;
  return template
    .split(/\n\s*\n/)
    .filter((paragraph) => !empty.some((p) => paragraph.includes(p)))
    .join('\n\n');
}

export function renderWelcomeMessage(template: string, vars: WelcomeMessageVars): string {
  return (
    dropEmptyEventParagraphs(template, vars)
      .replaceAll('${FIRST_NAME}', vars.name)
      .replaceAll('${SENDER_NAME}', vars.senderName)
      .replaceAll('${MAGIC_LINK}', vars.magicLink ?? '')
      // Retired placeholder — swallow it so a template saved before it was
      // dropped doesn't send the literal ${RSVP_LINK} text.
      .replaceAll('${RSVP_LINK}', '')
      .replaceAll('${WHATSAPP_LINK}', vars.whatsappLink)
      // Replacer functions keep `$&` / `$$` in event titles literal.
      .replaceAll('${NEXT_OFFICIAL_EVENT}', () => vars.nextOfficialEvent ?? '')
      .replaceAll('${CLUB_EVENT}', () => vars.clubEvent ?? '')
  );
}

export function buildSmsHref(phoneNumber: string, body?: string): string {
  if (!body) return `sms:${phoneNumber}`;
  // iOS expects `&body=` after the number; Android/others use `?body=`.
  // Using the wrong separator on iOS causes Messages to show the raw URL
  // instead of opening a draft.
  const isIos = /iPad|iPhone|iPod/.test(navigator.userAgent);
  const separator = isIos ? '&' : '?';
  return `sms:${phoneNumber}${separator}body=${encodeURIComponent(body)}`;
}

// wa.me deeplink — works with personal WhatsApp; no business API needed.
// Phone must be digits-only (E.164 minus the `+`).
export function buildWhatsAppHref(phoneNumber: string, body?: string): string {
  const digits = phoneNumber.replace(/\D/g, '');
  if (!body) return `https://wa.me/${digits}`;
  return `https://wa.me/${digits}?text=${encodeURIComponent(body)}`;
}
