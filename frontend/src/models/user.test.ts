import { describe, expect, it } from 'vitest';

import { makeUser as makeSharedUser } from '@/test/fixtures';

import { consentRedirect, passwordSetupRedirect, postAuthRedirect, type User } from './user';

function makeUser(overrides: Partial<User> = {}): User {
  return makeSharedUser({
    id: 'u1',
    firstName: 'Alice',
    lastName: 'Anderson',
    fullName: 'Alice Anderson',
    email: 'alice@example.com',
    ...overrides,
  });
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

  it('uses firstName presence for the name check', () => {
    const noFirstName = makeUser({
      firstName: '',
      email: 'a@b.c',
      needsOnboarding: true,
    });
    expect(passwordSetupRedirect(noFirstName)).toBe('/onboarding'); // no first name → onboarding
    const named = makeUser({
      firstName: 'Ada',
      email: 'a@b.c',
      needsOnboarding: true,
      needsPasswordReset: false,
    });
    expect(passwordSetupRedirect(named)).toBe('/new-password'); // has name + email
  });
});

describe('consentRedirect', () => {
  it('returns null when every consent is on file', () => {
    expect(consentRedirect(makeUser())).toBeNull();
  });

  it('returns /consent when guidelines consent is pending', () => {
    expect(consentRedirect(makeUser({ needsGuidelinesConsent: true }))).toBe('/consent');
  });

  it('returns /consent when only sms consent is pending', () => {
    expect(consentRedirect(makeUser({ needsSmsConsent: true }))).toBe('/consent');
  });

  it('returns /consent when both consents are pending', () => {
    expect(consentRedirect(makeUser({ needsGuidelinesConsent: true, needsSmsConsent: true }))).toBe(
      '/consent',
    );
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

  it('routes an sms-only consent-pending user to /consent', () => {
    expect(postAuthRedirect(makeUser({ needsSmsConsent: true }))).toBe('/consent');
  });

  it('prioritises password setup over consent when both are pending', () => {
    const target = postAuthRedirect(
      makeUser({ needsOnboarding: true, firstName: '', needsGuidelinesConsent: true }),
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
