import 'package:flutter_test/flutter_test.dart';
import 'package:pda/utils/validators.dart' as v;

void main() {
  group('displayName()', () {
    final validator = v.displayName();

    test('accepts ASCII name', () {
      expect(validator('Alex R'), isNull);
    });

    test('accepts name with hyphen', () {
      expect(validator('Mary-Jane'), isNull);
    });

    test('accepts name with apostrophe', () {
      expect(validator("O'Brien"), isNull);
    });

    test('accepts name with period (initial)', () {
      expect(validator('Alex R.'), isNull);
    });

    test('accepts accented Latin characters', () {
      expect(validator('José Müller'), isNull);
    });

    test('accepts Cyrillic characters', () {
      expect(validator('Юлия К'), isNull);
    });

    test('accepts CJK characters', () {
      expect(validator('田中 太郎'), isNull);
    });

    test('rejects empty string', () {
      expect(validator(''), isNotNull);
    });

    test('rejects whitespace only', () {
      expect(validator('   '), isNotNull);
    });

    test('rejects name with digits', () {
      expect(validator('Alice2'), isNotNull);
    });

    test('rejects email address', () {
      expect(validator('user@example.com'), isNotNull);
    });

    test('rejects URL', () {
      expect(validator('http://evil.com'), isNotNull);
    });

    test('rejects phone number', () {
      expect(validator('5551234567'), isNotNull);
    });

    test('rejects names over 64 characters', () {
      expect(validator('A' * 65), isNotNull);
    });
  });

  group('password()', () {
    final validator = v.password();

    test('rejects empty string', () {
      expect(validator(''), isNotNull);
    });

    test('rejects null', () {
      expect(validator(null), isNotNull);
    });

    test('rejects password under 12 characters', () {
      expect(validator('Short1!'), isNotNull);
    });

    test('rejects missing uppercase', () {
      expect(validator('nouppercase123!'), isNotNull);
    });

    test('rejects missing number', () {
      expect(validator('NoNumberHere!!!'), isNotNull);
    });

    test('rejects missing special character', () {
      expect(validator('NoSpecialChar1X'), isNotNull);
    });

    test('accepts valid password', () {
      expect(validator('ValidPass123!'), isNull);
    });

    test('accepts password with exactly 12 characters', () {
      expect(validator('Abcdefghij1!'), isNull);
    });

    test('accepts various special characters', () {
      expect(validator('ValidPass123@'), isNull);
      expect(validator('ValidPass123#'), isNull);
      expect(validator('ValidPass123\$'), isNull);
    });
  });

  group('optionalDisplayName()', () {
    final validator = v.optionalDisplayName();

    test('accepts empty/null (optional field)', () {
      expect(validator(''), isNull);
      expect(validator(null), isNull);
      expect(validator('   '), isNull);
    });

    test('accepts valid Unicode name when provided', () {
      expect(validator("Mary-Jane O'Brien"), isNull);
    });

    test('rejects invalid name when provided', () {
      expect(validator('user@example.com'), isNotNull);
      expect(validator('Alice2'), isNotNull);
    });

    test('rejects names over 64 characters', () {
      expect(validator('A' * 65), isNotNull);
    });
  });
}
