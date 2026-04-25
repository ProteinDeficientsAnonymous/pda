// UI copy for machine-readable validation errors.
//
// Backend raises ValidationException(code, field, params?) and a global Ninja
// handler reshapes those (plus Pydantic errors) into
// { detail: [{ code, field, params? }, ...] }.
//
// The `Code` tree and `ValidationCode` union are generated from the backend
// (see validationCodes.gen.ts). This file owns the UI copy for each code and
// re-exports `Code` with an added FE-only `Generic` namespace for the
// Pydantic-shape codes the handler emits.
//
// Adding a code:
//   1. Add the constant in backend/community/_validation.py.
//   2. Run `make generate-codes` (regenerates validationCodes.gen.ts).
//   3. Add a `case` in messageForKnownCode() below — TS will fail the build
//      until every generated code has a case.

import { Code as GeneratedCode, type ValidationCode } from './validationCodes.gen';

/**
 * FE-only codes. The global error handler emits these for generic Pydantic
 * errors (type coerce failures, missing fields) that don't map to a domain
 * ValidationException. Kept separate from the generated backend catalog.
 */
const GenericCodes = {
  FieldRequired: 'field_required',
  FieldInvalid: 'field_invalid',
} as const;

export type GenericCode = (typeof GenericCodes)[keyof typeof GenericCodes];

export const Code = {
  ...GeneratedCode,
  Generic: GenericCodes,
} as const;

export type { ValidationCode };

/**
 * Every code FE knows how to render. Includes both backend codes (generated
 * from the Code catalog) and FE-only Generic codes. Used to give
 * `messageForKnownCode` an exhaustiveness check at the type level.
 */
export type KnownCode = ValidationCode | GenericCode;

export interface FieldError {
  code: string;
  field: string | null;
  params?: Record<string, unknown>;
}

/** Return user-facing copy for a single field error. */
export function messageForCode(err: FieldError): string {
  if (isKnownCode(err.code)) {
    return messageForKnownCode(err.code, err);
  }
  return "something's not right — double-check your entries";
}

/**
 * Exhaustive over `KnownCode`. Adding a new code to the backend will fail the
 * build here until a `case` is added, eliminating silent fallbacks for
 * codes the FE forgot to ship copy for.
 */
function messageForKnownCode(code: KnownCode, err: FieldError): string {
  switch (code) {
    // Event
    case Code.Event.NotFound:
      return 'event not found';
    case Code.Event.StartDatetimeRequiredUnlessTbd:
      return 'pick a start time, or mark the time as tbd';
    case Code.Event.MaxAttendeesMustBeAtLeastOne:
      return 'max attendees must be at least 1 — leave blank for unlimited';
    case Code.Event.StartDatetimeMustBeFuture:
      return 'start date must be in the future';
    case Code.Event.EndBeforeStart:
      return 'end time must be after the start time';
    case Code.Event.AttendanceInvalidChoice:
      return 'pick a valid attendance option';
    case Code.Event.OfficialMustBePublic:
      return 'official events must be public';
    case Code.Event.InvalidCreateStatus:
      return 'new events can only be saved as active or draft';
    case Code.Event.DateLockedByPoll:
      return "can't edit the date while a poll is active — finalize the poll first";
    case Code.Event.InviteOnly:
      return 'this event is invite only';
    case Code.Event.AuthRequired:
      return 'you need to sign in for that';
    case Code.Event.CancelledCannotBeEdited:
      return "cancelled events can't be edited";
    case Code.Event.PastCannotBeCancelled:
      return "past events can't be cancelled — delete instead";
    case Code.Event.NoAttendeesCannotBeCancelled:
      return "events with no invited users or rsvps can't be cancelled — delete instead";
    case Code.Event.InvalidStatusTransition:
      return 'invalid status change';
    case Code.Event.CancelBeforeDelete:
      return 'cancel this event before deleting it';
    case Code.Event.RsvpInvalidStatus:
      return 'invalid rsvp status';
    case Code.Event.FlagAlreadyFlagged:
      return "you've already flagged this event";
    case Code.Event.FlagInvalidAction:
      return 'invalid flag action';
    case Code.Event.RsvpsNotEnabled:
      return 'rsvps are not enabled for this event';
    case Code.Event.RsvpsClosedCancelled:
      return 'rsvps are closed for cancelled events';
    case Code.Event.RsvpsClosedPast:
      return 'rsvps are closed for past events';
    case Code.Event.NoPlusOneSpots:
      return 'no spots available for a +1';
    case Code.Event.RsvpNotFound:
      return 'rsvp not found';
    case Code.Event.AttendanceOpensLater:
      return 'check-in opens an hour before the event starts';
    case Code.Event.AttendanceOnlyForGoingRsvps:
      return 'attendance can only be marked on going rsvps';

    // Poll
    case Code.Poll.NotFound:
      return 'poll not found';
    case Code.Poll.OptionsRequired:
      return 'a poll requires at least 1 option';
    case Code.Poll.OptionsMustBeFuture:
      return 'poll options must be in the future';
    case Code.Poll.EventAlreadyHasPoll:
      return 'this event already has a poll';
    case Code.Poll.OptionNotFound:
      return 'poll option not found';
    case Code.Poll.OptionAlreadyExists:
      return 'that time is already an option in this poll';
    case Code.Poll.CannotModifyFinalized:
      return 'cannot modify a finalized poll';
    case Code.Poll.AlreadyFinalized:
      return 'this poll has already been finalized';
    case Code.Poll.WinningOptionNotFound:
      return 'winning option not found in this poll';
    case Code.Poll.MinTwoOptions:
      return 'a poll must have at least 2 options';
    case Code.Poll.InvalidAvailability:
      return 'availability must be "yes", "maybe", or "no"';

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
      return 'partiful link must be a partiful.com url';

    // Phone
    case Code.Phone.Invalid:
      return "that doesn't look like a valid phone number";
    case Code.Phone.AlreadyExists:
      return 'a member with that phone number already exists';

    // Zelle
    case Code.Zelle.Invalid:
      return 'zelle must be an email address or phone number';

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

    // User (admin actions)
    case Code.User.NotFound:
      return 'user not found';
    case Code.User.CannotDeleteSelf:
      return "you can't delete your own account";
    case Code.User.CannotDeleteLastAdmin:
      return "can't delete the last admin — promote someone else first";
    case Code.User.AlreadyArchived:
      return 'this user is already archived';
    case Code.User.CannotPauseSelf:
      return "you can't pause your own account";
    case Code.User.CannotPauseAdmin:
      return "admins can't be paused";
    case Code.User.RoleIdsNotFound:
      return 'one or more role IDs not found';

    // Survey
    case Code.Survey.NotFound:
      return 'survey not found';
    case Code.Survey.SlugAlreadyExists:
      return 'a survey with that slug already exists';
    case Code.Survey.QuestionNotFound:
      return 'question not found';
    case Code.Survey.NoDatetimePollQuestion:
      return 'survey has no datetime poll question';
    case Code.Survey.WinningDatetimeNotInOptions:
      return 'winning datetime is not one of the poll options';
    case Code.Survey.PollAlreadyFinalized:
      return 'this poll has already been finalized';
    case Code.Survey.AnswerRequired: {
      const label = typeof err.params?.label === 'string' ? err.params.label : null;
      return label ? `"${label}" is required` : 'an answer is required';
    }
    case Code.Survey.AnswerInvalidFormat: {
      const label = typeof err.params?.label === 'string' ? err.params.label : null;
      return label ? `invalid answer format for "${label}"` : 'invalid answer format';
    }
    case Code.Survey.AnswerInvalidOption: {
      const label = typeof err.params?.label === 'string' ? err.params.label : null;
      return label ? `invalid option for "${label}"` : 'invalid option';
    }
    case Code.Survey.AnswerMustBeNumber: {
      const label = typeof err.params?.label === 'string' ? err.params.label : null;
      return label ? `"${label}" must be a number` : 'must be a number';
    }
    case Code.Survey.AnswerMustBeYesNo: {
      const label = typeof err.params?.label === 'string' ? err.params.label : null;
      return label ? `"${label}" must be yes or no` : 'must be yes or no';
    }
    case Code.Survey.AnswerRatingOutOfRange: {
      const label = typeof err.params?.label === 'string' ? err.params.label : null;
      return label ? `"${label}" must be between 1 and 5` : 'rating must be between 1 and 5';
    }
    case Code.Survey.AnswerInvalidDatetimeOption: {
      const label = typeof err.params?.label === 'string' ? err.params.label : null;
      return label ? `invalid datetime option for "${label}"` : 'invalid datetime option';
    }
    case Code.Survey.AnswerInvalidAvailability: {
      const label = typeof err.params?.label === 'string' ? err.params.label : null;
      return label
        ? `availability for "${label}" must be "yes" or "maybe"`
        : 'availability must be "yes" or "maybe"';
    }

    // Join request
    case Code.JoinRequest.NotFound:
      return 'join request not found';
    case Code.JoinRequest.AlreadyDecided:
      return 'this request has already been decided';
    case Code.JoinRequest.OnlyRejectedCanBeUnRejected:
      return 'only rejected requests can be un-rejected';
    case Code.JoinRequest.PhoneAlreadyInvited:
      return 'that number is already in the community — try logging in instead';
    case Code.JoinRequest.PhoneAlreadyPending:
      return "a request for this number is already pending — we'll be in touch soon";
    case Code.JoinRequest.AnswerRequired: {
      const label = typeof err.params?.label === 'string' ? err.params.label : null;
      return label ? `"${label}" is required` : 'an answer is required';
    }
    case Code.JoinRequest.AnswerTooLong: {
      const label = typeof err.params?.label === 'string' ? err.params.label : null;
      const max = typeof err.params?.max === 'number' ? err.params.max : null;
      if (label && max !== null) return `"${label}" must be at most ${String(max)} characters`;
      return 'that answer is too long';
    }
    case Code.JoinRequest.AnswerInvalidOption: {
      const label = typeof err.params?.label === 'string' ? err.params.label : null;
      return label ? `invalid option for "${label}"` : 'invalid option';
    }
    case Code.JoinRequest.InvalidStatus:
      return 'invalid status for this action';

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

    // Page / Docs / JoinForm / Feedback / Notification
    case Code.Page.MembersOnly:
      return 'members only';
    case Code.Docs.FolderNotFound:
      return 'folder not found';
    case Code.Docs.ParentFolderNotFound:
      return 'parent folder not found';
    case Code.Docs.DocumentNotFound:
      return 'document not found';
    case Code.JoinForm.QuestionNotFound:
      return 'question not found';
    case Code.Feedback.NotConfigured:
      return 'feedback submission is not configured';
    case Code.Feedback.CreationFailed:
      return "couldn't submit feedback — try again";
    case Code.Notification.NotFound:
      return 'notification not found';

    // Welcome template
    case Code.WelcomeTemplate.BodyRequired:
      return 'welcome message body is required';
    case Code.WelcomeTemplate.BodyTooLong: {
      const max = typeof err.params?.max_length === 'number' ? err.params.max_length : null;
      return max !== null
        ? `welcome message must be at most ${String(max)} characters`
        : 'welcome message is too long';
    }

    // Generic (FE-only, emitted for Pydantic errors without a ValidationException)
    case Code.Generic.FieldRequired:
      return err.field ? `${err.field.replace(/_/g, ' ')} is required` : 'this field is required';
    case Code.Generic.FieldInvalid:
      return err.field ? `${err.field.replace(/_/g, ' ')} is not valid` : 'this field is not valid';

    default:
      return assertNever(code);
  }
}

// If TS flags this line with "Argument of type 'X' is not assignable to
// parameter of type 'never'", the named code has no case in the switch above.
// Add one, then re-run `pnpm typecheck`.
function assertNever(code: never): never {
  throw new Error(`unhandled validation code: ${String(code)}`);
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

function isKnownCode(code: string): code is KnownCode {
  return KNOWN_CODES.has(code);
}

const KNOWN_CODES: ReadonlySet<string> = new Set<string>([...collectCodeValues(Code)]);

function collectCodeValues(tree: Record<string, unknown>): string[] {
  const out: string[] = [];
  for (const value of Object.values(tree)) {
    if (typeof value === 'string') {
      out.push(value);
    } else if (value && typeof value === 'object') {
      out.push(...collectCodeValues(value as Record<string, unknown>));
    }
  }
  return out;
}

function extractStringArray(params: Record<string, unknown> | undefined, key: string): string[] {
  const value = params?.[key];
  if (!Array.isArray(value)) return [];
  return value.filter((v): v is string => typeof v === 'string');
}
