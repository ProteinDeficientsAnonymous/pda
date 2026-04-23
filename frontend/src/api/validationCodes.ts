// Machine-readable validation error codes from the backend.
// The backend raises ValidationException(code, field, params?) and a global
// Ninja handler reshapes those (and generic Pydantic errors) into
// { detail: [{ code, field, params? }, ...] }.
//
// This file mirrors backend/community/_validation.py — the string values must
// match exactly. UI copy lives here (all user-facing text is owned by the FE).
//
// To add a new code:
//   1. Add the constant to Code.<Domain> below AND the backend's Code.<Domain>
//      (identical string value).
//   2. Add a case in messageForCode() below.
//
// Unknown codes fall back to a generic message — never display the raw code.

/**
 * Namespaced validation codes. String values are the API contract —
 * never rename once shipped. Mirrors backend Code class.
 */
export const Code = {
  Event: {
    StartDatetimeRequiredUnlessTbd: 'event.start_datetime_required_unless_tbd',
    MaxAttendeesMustBeAtLeastOne: 'event.max_attendees_must_be_at_least_one',
    AttendanceInvalidChoice: 'event.attendance_invalid_choice',
  },
  Url: {
    Invalid: 'url.invalid',
    PathRequired: 'url.path_required',
    SchemeMustBeHttpOrHttps: 'url.scheme_must_be_http_or_https',
    WhatsappNotRecognized: 'url.whatsapp_not_recognized',
    PartifulNotRecognized: 'url.partiful_not_recognized',
  },
  Phone: {
    Invalid: 'phone.invalid',
    Required: 'phone.required',
    AlreadyExists: 'phone.already_exists',
  },
  DisplayName: {
    Required: 'display_name.required',
    TooLong: 'display_name.too_long',
    InvalidChars: 'display_name.invalid_chars',
    NeedsALetter: 'display_name.needs_a_letter',
  },
  Auth: {
    InvalidCredentials: 'auth.invalid_credentials',
    AccountArchived: 'auth.account_archived',
    AccountPaused: 'auth.account_paused',
    MagicLinkInvalidOrExpired: 'auth.magic_link_invalid_or_expired',
    MagicLinkAlreadyUsed: 'auth.magic_link_already_used',
    AlreadySignedInAsDifferentUser: 'auth.already_signed_in_as_different_user',
    RefreshTokenInvalid: 'auth.refresh_token_invalid',
    RefreshFailed: 'auth.refresh_failed',
    CurrentPasswordIncorrect: 'auth.current_password_incorrect',
  },
  Password: {
    Invalid: 'password.invalid',
  },
  Role: {
    NotFound: 'role.not_found',
    NameAlreadyExists: 'role.name_already_exists',
    ProtectedCannotEdit: 'role.protected_cannot_edit',
    ProtectedCannotRename: 'role.protected_cannot_rename',
    ProtectedCannotDelete: 'role.protected_cannot_delete',
    CannotRemoveOwnAdmin: 'role.cannot_remove_own_admin',
    CannotRemoveLastAdmin: 'role.cannot_remove_last_admin',
    MemberRoleRequired: 'role.member_role_required',
  },
  Member: {
    NotFound: 'member.not_found',
  },
  Photo: {
    TypeNotAllowed: 'photo.type_not_allowed',
    TooLarge: 'photo.too_large',
  },
  Perm: {
    Denied: 'perm.denied',
  },
  Rate: {
    Limited: 'rate.limited',
  },

  // Generic fallbacks emitted by the handler for Pydantic errors without
  // a custom code (type mismatches, missing fields, etc.).
  Generic: {
    FieldRequired: 'field_required',
    FieldInvalid: 'field_invalid',
  },
} as const;

export interface FieldError {
  code: string;
  field: string | null;
  params?: Record<string, unknown>;
}

/** Return user-facing copy for a single field error. */
export function messageForCode(err: FieldError): string {
  switch (err.code) {
    // Event
    case Code.Event.StartDatetimeRequiredUnlessTbd:
      return 'pick a start time, or mark the time as tbd';
    case Code.Event.MaxAttendeesMustBeAtLeastOne:
      return 'max attendees must be at least 1 — leave blank for unlimited';
    case Code.Event.AttendanceInvalidChoice:
      return 'pick a valid attendance option';

    // URL
    case Code.Url.Invalid:
      return 'enter a valid url';
    case Code.Url.PathRequired:
      return 'link must point to a specific page, not just a homepage';
    case Code.Url.SchemeMustBeHttpOrHttps:
      return 'url must start with http:// or https://';
    case Code.Url.WhatsappNotRecognized:
      return 'whatsapp link must be from chat.whatsapp.com, wa.me, or whats.app';
    case Code.Url.PartifulNotRecognized:
      return 'link must be a partiful.com url';

    // Phone
    case Code.Phone.Required:
      return 'phone number is required';
    case Code.Phone.Invalid:
      return "that doesn't look like a valid phone number";
    case Code.Phone.AlreadyExists:
      return 'a member with that phone number already exists';

    // Display name
    case Code.DisplayName.Required:
      return 'display name is required';
    case Code.DisplayName.TooLong: {
      const max = typeof err.params?.max_length === 'number' ? err.params.max_length : null;
      return max !== null
        ? `display name must be at most ${String(max)} characters`
        : 'display name is too long';
    }
    case Code.DisplayName.InvalidChars:
      return 'display name can only have letters, spaces, apostrophes, hyphens, and periods';
    case Code.DisplayName.NeedsALetter:
      return 'display name must contain at least one letter';

    // Auth
    case Code.Auth.InvalidCredentials:
      return "that phone number and password don't match — try again";
    case Code.Auth.AccountArchived:
      return 'this account is no longer active';
    case Code.Auth.AccountPaused:
      return 'your membership is currently paused';
    case Code.Auth.MagicLinkInvalidOrExpired:
      return 'this login link is invalid or has expired';
    case Code.Auth.MagicLinkAlreadyUsed:
      return 'this login link has already been used';
    case Code.Auth.AlreadySignedInAsDifferentUser:
      return "you're signed in as a different user — log out first";
    case Code.Auth.RefreshTokenInvalid:
    case Code.Auth.RefreshFailed:
      return 'your session expired — please sign in again';
    case Code.Auth.CurrentPasswordIncorrect:
      return "current password doesn't match";

    // Password
    case Code.Password.Invalid: {
      const reasons = extractStringArray(err.params, 'reasons');
      if (reasons.length > 0) return reasons.join(' · ');
      return 'password is not strong enough';
    }

    // Role
    case Code.Role.NotFound:
      return 'role not found';
    case Code.Role.NameAlreadyExists:
      return 'a role with that name already exists';
    case Code.Role.ProtectedCannotEdit: {
      const name = typeof err.params?.role_name === 'string' ? err.params.role_name : null;
      return name
        ? `the "${name}" role is built-in and can't be edited`
        : "this role is built-in and can't be edited";
    }
    case Code.Role.ProtectedCannotRename: {
      const name = typeof err.params?.role_name === 'string' ? err.params.role_name : null;
      return name
        ? `the "${name}" role is built-in and can't be renamed`
        : "this role is built-in and can't be renamed";
    }
    case Code.Role.ProtectedCannotDelete: {
      const name = typeof err.params?.role_name === 'string' ? err.params.role_name : null;
      return name
        ? `the "${name}" role is built-in and can't be deleted`
        : "this role is built-in and can't be deleted";
    }
    case Code.Role.CannotRemoveOwnAdmin:
      return "you can't remove your own admin role";
    case Code.Role.CannotRemoveLastAdmin:
      return "can't remove admin from the last admin — promote someone else first";
    case Code.Role.MemberRoleRequired:
      return 'every user must keep the member role';

    // Member
    case Code.Member.NotFound:
      return 'member not found';

    // Photo
    case Code.Photo.TypeNotAllowed:
      return 'photo must be a jpeg, png, webp, or gif';
    case Code.Photo.TooLarge: {
      const maxMb = typeof err.params?.max_mb === 'number' ? err.params.max_mb : null;
      return maxMb !== null ? `photo must be under ${String(maxMb)} mb` : 'photo is too large';
    }

    // Permission / rate
    case Code.Perm.Denied:
      return "you don't have permission to do that";
    case Code.Rate.Limited:
      return "you're going too fast — try again in a moment";

    // Generic fallbacks
    case Code.Generic.FieldRequired:
      return err.field ? `${err.field.replace(/_/g, ' ')} is required` : 'this field is required';
    case Code.Generic.FieldInvalid:
      return err.field ? `${err.field.replace(/_/g, ' ')} is not valid` : 'this field is not valid';

    default:
      return "something's not right — double-check your entries";
  }
}

/** Join multiple field errors into a single human-readable sentence. */
export function messagesFromFieldErrors(errors: FieldError[]): string {
  const msgs = errors.map(messageForCode);
  // Dedup while preserving order — backend sometimes emits two errors for
  // the same underlying mistake (type coerce + validator).
  const seen = new Set<string>();
  const uniq = msgs.filter((m) => {
    if (seen.has(m)) return false;
    seen.add(m);
    return true;
  });
  return uniq.join(' · ');
}

function extractStringArray(params: Record<string, unknown> | undefined, key: string): string[] {
  const value = params?.[key];
  if (!Array.isArray(value)) return [];
  return value.filter((v): v is string => typeof v === 'string');
}
