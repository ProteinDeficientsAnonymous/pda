import type { User } from './user';

export const ConsentType = {
  Guidelines: 'guidelines',
  Sms: 'sms',
  ContactPrivacy: 'contact_privacy',
} as const;
export type ConsentTypeValue = (typeof ConsentType)[keyof typeof ConsentType];

export interface ConsentDescriptor {
  type: ConsentTypeValue;
  needsConsent: (user: User) => boolean;
  before: string;
  linkLabel: string;
  linkTo: string;
  after?: string;
}

export const CONSENT_REGISTRY: readonly ConsentDescriptor[] = [
  {
    type: ConsentType.Guidelines,
    needsConsent: (u) => u.needsGuidelinesConsent,
    before: 'i have read and agree to the ',
    linkLabel: 'community guidelines',
    linkTo: '/guidelines',
    after: ' and community agreements',
  },
  {
    type: ConsentType.Sms,
    needsConsent: (u) => u.needsSmsConsent,
    before: 'i agree to the ',
    linkLabel: 'sms policy',
    linkTo: '/sms-policy',
  },
];

export function missingConsents(user: User | null): ConsentDescriptor[] {
  if (!user) return [];
  return CONSENT_REGISTRY.filter((c) => c.needsConsent(user));
}
