// Machine-readable validation error codes from the backend.
// The backend raises ValidationException(code, field, params?) and a global
// Ninja handler reshapes those (and generic Pydantic errors) into
// { detail: [{ code, field, params? }, ...] }. UI copy lives here.
//
// To add a new code:
//   1. Add the constant to the backend ValidationCode class (same string).
//   2. Add it to ValidationCode below.
//   3. Add a case in messageForCode().
//
// Unknown codes fall back to a generic "something's not right" message —
// safe, if unhelpful. Never display the raw code to users.

export const ValidationCode = {
  // Event form
  StartDatetimeRequiredUnlessTbd: 'start_datetime_required_unless_tbd',
  MaxAttendeesMustBeAtLeastOne: 'max_attendees_must_be_at_least_one',
  UrlInvalid: 'url_invalid',
  UrlPathRequired: 'url_path_required',
  UrlSchemeMustBeHttpOrHttps: 'url_scheme_must_be_http_or_https',
  WhatsappUrlNotRecognized: 'whatsapp_url_not_recognized',
  PartifulUrlNotRecognized: 'partiful_url_not_recognized',

  // Event attendance
  AttendanceInvalidChoice: 'attendance_invalid_choice',

  // Generic fallbacks emitted by the handler for Pydantic errors without
  // a custom code (type mismatches, missing fields, etc.).
  FieldRequired: 'field_required',
  FieldInvalid: 'field_invalid',
} as const;

export type ValidationCodeValue = (typeof ValidationCode)[keyof typeof ValidationCode];

export interface FieldError {
  code: string;
  field: string | null;
  params?: Record<string, unknown>;
}

/** Return user-facing copy for a single field error. */
export function messageForCode(err: FieldError): string {
  switch (err.code) {
    case ValidationCode.StartDatetimeRequiredUnlessTbd:
      return 'pick a start time, or mark the time as tbd';
    case ValidationCode.MaxAttendeesMustBeAtLeastOne:
      return 'max attendees must be at least 1 — leave blank for unlimited';
    case ValidationCode.UrlInvalid:
      return 'enter a valid url';
    case ValidationCode.UrlPathRequired:
      return 'link must point to a specific page, not just a homepage';
    case ValidationCode.UrlSchemeMustBeHttpOrHttps:
      return 'url must start with http:// or https://';
    case ValidationCode.WhatsappUrlNotRecognized:
      return 'whatsapp link must be from chat.whatsapp.com, wa.me, or whats.app';
    case ValidationCode.PartifulUrlNotRecognized:
      return 'link must be a partiful.com url';
    case ValidationCode.AttendanceInvalidChoice:
      return 'pick a valid attendance option';
    case ValidationCode.FieldRequired:
      return err.field ? `${err.field.replace(/_/g, ' ')} is required` : 'this field is required';
    case ValidationCode.FieldInvalid:
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
