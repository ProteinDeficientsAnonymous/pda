/// Shared form field validators.
///
/// Each method returns a [FormFieldValidator] — a function `(String?) -> String?`
/// where `null` means valid. Compose them with [all] when multiple rules apply.
library;

typedef Validator = String? Function(String?);

/// Runs [validators] in order and returns the first error, or null if all pass.
Validator all(List<Validator> validators) {
  return (value) {
    for (final v in validators) {
      final error = v(value);
      if (error != null) return error;
    }
    return null;
  };
}

/// Field must be non-empty.
Validator required([String message = 'Required']) {
  return (v) => (v == null || v.trim().isEmpty) ? message : null;
}

/// Value must not exceed [max] characters (trims first).
Validator maxLength(int max) {
  return (v) {
    if (v == null) return null;
    if (v.trim().length > max) return 'Max $max characters';
    return null;
  };
}

/// Value must be at least [min] characters if non-empty (trims first).
Validator minLength(int min, [String? message]) {
  return (v) {
    if (v == null || v.trim().isEmpty) return null;
    if (v.trim().length < min) {
      return message ?? 'At least $min characters required';
    }
    return null;
  };
}

/// Unicode letters, combining marks, apostrophes, hyphens, spaces, and periods.
/// Rejects digits and symbols (emails, phone numbers, URLs).
Validator displayName() {
  final re = RegExp(r"^[\p{L}\p{M}' \-\.]+$", unicode: true);
  return all([
    required(),
    (v) => (v != null && v.trim().isNotEmpty && !re.hasMatch(v.trim()))
        ? 'letters, spaces, hyphens, and apostrophes only'
        : null,
    maxLength(64),
  ]);
}

/// Optional display name: skips format check if empty, same rules if provided.
Validator optionalDisplayName() {
  final re = RegExp(r"^[\p{L}\p{M}' \-\.]+$", unicode: true);
  return all([
    (v) => (v != null && v.trim().isNotEmpty && !re.hasMatch(v.trim()))
        ? 'letters, spaces, hyphens, and apostrophes only'
        : null,
    maxLength(64),
  ]);
}

/// Optional email: skips if empty, validates format if provided.
Validator optionalEmail() {
  final re = RegExp(
    r'^[a-zA-Z0-9.!#$%&*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$',
  );
  return (v) {
    if (v == null || v.trim().isEmpty) return null;
    if (!re.hasMatch(v.trim())) return 'enter a valid email address';
    return null;
  };
}

/// Optional URL: skips if empty, validates scheme + authority if provided.
/// Pass [httpsOnly] to reject non-https URLs.
Validator optionalUrl({bool httpsOnly = false}) {
  return (v) {
    if (v == null || v.trim().isEmpty) return null;
    final s = v.trim();
    final normalized = s.startsWith('http') ? s : 'https://$s';
    final uri = Uri.tryParse(normalized);
    if (uri == null || !uri.hasAuthority) return 'Enter a valid URL';
    if (httpsOnly && uri.scheme != 'https') return 'URL must use https';
    return null;
  };
}

/// Password strength: 12+ chars, uppercase letter, number, special character.
Validator password() {
  return all([
    required(),
    (v) => (v != null && v.length < 12) ? 'at least 12 characters' : null,
    (v) => (v != null && v.isNotEmpty && !RegExp(r'[A-Z]').hasMatch(v))
        ? 'include an uppercase letter'
        : null,
    (v) => (v != null && v.isNotEmpty && !RegExp(r'[0-9]').hasMatch(v))
        ? 'include a number'
        : null,
    (v) => (v != null && v.isNotEmpty && !RegExp(r'[^A-Za-z0-9]').hasMatch(v))
        ? 'include a special character'
        : null,
  ]);
}

/// Role name: required, alphanumeric + underscores/hyphens, max 50 chars.
Validator roleName() {
  final re = RegExp(r'^[a-zA-Z0-9_\-]+$');
  return all([
    required(),
    (v) => (v != null && v.trim().isNotEmpty && !re.hasMatch(v.trim()))
        ? 'Letters, numbers, underscores and hyphens only'
        : null,
    maxLength(50),
  ]);
}
