import { describe, it, expect } from 'vitest';
import {
  displayName,
  password,
  optionalDisplayName,
  optionalEmail,
  optionalUrl,
  roleName,
  required,
  maxLength,
  minLength,
} from './validators';

describe('displayName', () => {
  it('accepts ASCII name', () => {
    expect(displayName('Alex R')).toBeNull();
  });

  it('accepts name with hyphen', () => {
    expect(displayName('Mary-Jane')).toBeNull();
  });

  it('accepts name with apostrophe', () => {
    expect(displayName("O'Brien")).toBeNull();
  });

  it('accepts name with period (initial)', () => {
    expect(displayName('Alex R.')).toBeNull();
  });

  it('accepts accented Latin characters', () => {
    expect(displayName('José Müller')).toBeNull();
  });

  it('accepts Cyrillic characters', () => {
    expect(displayName('Юлия К')).toBeNull();
  });

  it('accepts CJK characters', () => {
    expect(displayName('田中 太郎')).toBeNull();
  });

  it('rejects empty string', () => {
    expect(displayName('')).not.toBeNull();
  });

  it('rejects whitespace only', () => {
    expect(displayName('   ')).not.toBeNull();
  });

  it('rejects name with digits', () => {
    expect(displayName('Alice2')).not.toBeNull();
  });

  it('rejects email address', () => {
    expect(displayName('user@example.com')).not.toBeNull();
  });

  it('rejects URL', () => {
    expect(displayName('http://evil.com')).not.toBeNull();
  });

  it('rejects phone number', () => {
    expect(displayName('5551234567')).not.toBeNull();
  });

  it('rejects names over 64 characters', () => {
    expect(displayName('A'.repeat(65))).not.toBeNull();
  });
});

describe('password', () => {
  it('rejects empty string', () => {
    expect(password('')).not.toBeNull();
  });

  it('rejects null', () => {
    expect(password(null)).not.toBeNull();
  });

  it('rejects password under 12 characters', () => {
    expect(password('Short1!')).not.toBeNull();
  });

  it('rejects missing uppercase', () => {
    expect(password('nouppercase123!')).not.toBeNull();
  });

  it('rejects missing number', () => {
    expect(password('NoNumberHere!!!')).not.toBeNull();
  });

  it('rejects missing special character', () => {
    expect(password('NoSpecialChar1X')).not.toBeNull();
  });

  it('accepts valid password', () => {
    expect(password('ValidPass123!')).toBeNull();
  });

  it('accepts password with exactly 12 characters', () => {
    expect(password('Abcdefghij1!')).toBeNull();
  });

  it('accepts various special characters', () => {
    expect(password('ValidPass123@')).toBeNull();
    expect(password('ValidPass123#')).toBeNull();
    expect(password('ValidPass123$')).toBeNull();
  });
});

describe('optionalDisplayName', () => {
  it('accepts empty/null (optional field)', () => {
    expect(optionalDisplayName('')).toBeNull();
    expect(optionalDisplayName(null)).toBeNull();
    expect(optionalDisplayName('   ')).toBeNull();
  });

  it('accepts valid Unicode name when provided', () => {
    expect(optionalDisplayName("Mary-Jane O'Brien")).toBeNull();
  });

  it('rejects invalid name when provided', () => {
    expect(optionalDisplayName('user@example.com')).not.toBeNull();
    expect(optionalDisplayName('Alice2')).not.toBeNull();
  });

  it('rejects names over 64 characters', () => {
    expect(optionalDisplayName('A'.repeat(65))).not.toBeNull();
  });
});

describe('optionalEmail', () => {
  it('accepts empty/null', () => {
    expect(optionalEmail('')).toBeNull();
    expect(optionalEmail(null)).toBeNull();
  });

  it('accepts valid email', () => {
    expect(optionalEmail('test@example.com')).toBeNull();
  });

  it('rejects invalid email', () => {
    expect(optionalEmail('not-an-email')).not.toBeNull();
  });
});

describe('optionalUrl', () => {
  it('accepts empty/null', () => {
    expect(optionalUrl('')).toBeNull();
    expect(optionalUrl(null)).toBeNull();
  });

  it('accepts valid URL', () => {
    expect(optionalUrl('https://example.com')).toBeNull();
    expect(optionalUrl('example.com')).toBeNull();
  });

  it('rejects http when httpsOnly', () => {
    expect(optionalUrl('http://example.com', { httpsOnly: true })).not.toBeNull();
    expect(optionalUrl('https://example.com', { httpsOnly: true })).toBeNull();
  });

  it('rejects bare domain when requirePath', () => {
    expect(optionalUrl('example.com', { requirePath: true })).not.toBeNull();
    expect(optionalUrl('example.com/page', { requirePath: true })).toBeNull();
  });
});

describe('roleName', () => {
  it('accepts alphanumeric with underscore and hyphen', () => {
    expect(roleName('admin')).toBeNull();
    expect(roleName('super-user')).toBeNull();
    expect(roleName('user_1')).toBeNull();
  });

  it('rejects empty', () => {
    expect(roleName('')).not.toBeNull();
  });

  it('rejects special characters', () => {
    expect(roleName('admin!')).not.toBeNull();
    expect(roleName('admin@')).not.toBeNull();
  });

  it('rejects over 50 characters', () => {
    expect(roleName('A'.repeat(51))).not.toBeNull();
  });
});

describe('required', () => {
  it('rejects empty string', () => {
    expect(required('')).not.toBeNull();
  });

  it('accepts non-empty', () => {
    expect(required('hello')).toBeNull();
  });
});

describe('maxLength', () => {
  const validator = maxLength(10);

  it('accepts string at max length', () => {
    expect(validator('1234567890')).toBeNull();
  });

  it('rejects string over max length', () => {
    expect(validator('12345678901')).not.toBeNull();
  });
});

describe('minLength', () => {
  const validator = minLength(5);

  it('accepts empty (minimum only applies if non-empty)', () => {
    expect(validator('')).toBeNull();
  });

  it('accepts string at min length', () => {
    expect(validator('12345')).toBeNull();
  });

  it('rejects string under min length', () => {
    expect(validator('1234')).not.toBeNull();
  });
});