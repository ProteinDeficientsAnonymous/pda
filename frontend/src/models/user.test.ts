import { describe, it, expect } from 'vitest';
import {
  guidelinesConsentRedirect,
  passwordSetupRedirect,
  postAuthRedirect,
  type User,
} from './user';

function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 'u1',
    phoneNumber: '+12125550001',
    displayName: 'Alice',
    email: 'alice@example.com',
    bio: '',
    isSuperuser: false,
    isStaff: false,
    needsOnboarding: false,
    needsPasswordReset: false,
    needsGuidelinesConsent: false,
    showPhone: false,
    showEmail: false,
    weekStart: 'sunday',
    calendarFeedScope: 'all',
    profilePhotoUrl: '',
    photoUpdatedAt: null,
    roles: [],
    ...overrides,
  };
}

describe('passwordSetupRedirect', () => {
  it('returns null when nothing is pending', () => {
    expect(passwordSetupRedirect(makeUser())).toBeNull();
  });

  it('returns /new-password for a reset user with name + email', () => {
    expect(passwordSetupRedirect(makeUser({ needsPasswordReset: true }))).toBe('/new-password');
  });

  it('returns /onboarding when name or email is missing', () => {
    expect(passwordSetupRedirect(makeUser({ needsOnboarding: true, email: '' }))).toBe(
      '/onboarding',
    );
  });
});

describe('guidelinesConsentRedirect', () => {
  it('returns null when consented', () => {
    expect(guidelinesConsentRedirect(makeUser())).toBeNull();
  });

  it('returns /consent when consent is pending', () => {
    expect(guidelinesConsentRedirect(makeUser({ needsGuidelinesConsent: true }))).toBe('/consent');
  });
});

describe('postAuthRedirect', () => {
  it('returns null for a fully set-up, consented user', () => {
    expect(postAuthRedirect(makeUser())).toBeNull();
  });

  it('returns null for a null user', () => {
    expect(postAuthRedirect(null)).toBeNull();
  });

  it('routes a consent-pending user to /consent', () => {
    // Regression: the post-login navigation used to ignore consent and lean on
    // OnboardingGate, which raced the lazy target route and showed a blank
    // screen. The resolver must surface /consent so auth screens navigate there.
    expect(postAuthRedirect(makeUser({ needsGuidelinesConsent: true }))).toBe('/consent');
  });

  it('prioritises password setup over consent when both are pending', () => {
    const target = postAuthRedirect(
      makeUser({ needsOnboarding: true, displayName: '', needsGuidelinesConsent: true }),
    );
    expect(target).toBe('/onboarding');
  });

  it('prioritises /new-password over consent for a reset user with name + email', () => {
    const target = postAuthRedirect(
      makeUser({ needsPasswordReset: true, needsGuidelinesConsent: true }),
    );
    expect(target).toBe('/new-password');
  });
});
