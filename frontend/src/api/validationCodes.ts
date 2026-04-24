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
    NotFound: 'event.not_found',
    StartDatetimeRequiredUnlessTbd: 'event.start_datetime_required_unless_tbd',
    MaxAttendeesMustBeAtLeastOne: 'event.max_attendees_must_be_at_least_one',
    StartDatetimeMustBeFuture: 'event.start_datetime_must_be_future',
    EndBeforeStart: 'event.end_before_start',
    AttendanceInvalidChoice: 'event.attendance_invalid_choice',
    OfficialMustBePublic: 'event.official_must_be_public',
    InvalidCreateStatus: 'event.invalid_create_status',
    DateLockedByPoll: 'event.date_locked_by_poll',
    InviteOnly: 'event.invite_only',
    AuthRequired: 'event.auth_required',
    CancelledCannotBeEdited: 'event.cancelled_cannot_be_edited',
    PastCannotBeCancelled: 'event.past_cannot_be_cancelled',
    NoAttendeesCannotBeCancelled: 'event.no_attendees_cannot_be_cancelled',
    InvalidStatusTransition: 'event.invalid_status_transition',
    CancelBeforeDelete: 'event.cancel_before_delete',
    FlagAlreadyFlagged: 'event.flag_already_flagged',
    FlagInvalidAction: 'event.flag_invalid_action',
    RsvpsNotEnabled: 'event.rsvps_not_enabled',
    RsvpsClosedCancelled: 'event.rsvps_closed_cancelled',
    RsvpsClosedPast: 'event.rsvps_closed_past',
    RsvpInvalidStatus: 'event.rsvp_invalid_status',
    NoPlusOneSpots: 'event.no_plus_one_spots',
    RsvpNotFound: 'event.rsvp_not_found',
    AttendanceOpensLater: 'event.attendance_opens_later',
    AttendanceOnlyForGoingRsvps: 'event.attendance_only_for_going_rsvps',
  },
  Poll: {
    NotFound: 'poll.not_found',
    OptionsRequired: 'poll.options_required',
    OptionsMustBeFuture: 'poll.options_must_be_future',
    EventAlreadyHasPoll: 'poll.event_already_has_poll',
    OptionNotFound: 'poll.option_not_found',
    OptionAlreadyExists: 'poll.option_already_exists',
    CannotModifyFinalized: 'poll.cannot_modify_finalized',
    AlreadyFinalized: 'poll.already_finalized',
    WinningOptionNotFound: 'poll.winning_option_not_found',
    MinTwoOptions: 'poll.min_two_options',
    InvalidAvailability: 'poll.invalid_availability',
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
  User: {
    NotFound: 'user.not_found',
    CannotDeleteSelf: 'user.cannot_delete_self',
    CannotDeleteLastAdmin: 'user.cannot_delete_last_admin',
    AlreadyArchived: 'user.already_archived',
    CannotPauseSelf: 'user.cannot_pause_self',
    CannotPauseAdmin: 'user.cannot_pause_admin',
    RoleIdsNotFound: 'user.role_ids_not_found',
  },
  Survey: {
    NotFound: 'survey.not_found',
    SlugAlreadyExists: 'survey.slug_already_exists',
    QuestionNotFound: 'survey.question_not_found',
    NoDatetimePollQuestion: 'survey.no_datetime_poll_question',
    WinningDatetimeNotInOptions: 'survey.winning_datetime_not_in_options',
    PollAlreadyFinalized: 'survey.poll_already_finalized',
    AnswerRequired: 'survey.answer_required',
    AnswerInvalidFormat: 'survey.answer_invalid_format',
    AnswerInvalidOption: 'survey.answer_invalid_option',
    AnswerMustBeNumber: 'survey.answer_must_be_number',
    AnswerMustBeYesNo: 'survey.answer_must_be_yes_no',
    AnswerRatingOutOfRange: 'survey.answer_rating_out_of_range',
    AnswerInvalidDatetimeOption: 'survey.answer_invalid_datetime_option',
    AnswerInvalidAvailability: 'survey.answer_invalid_availability',
  },
  JoinRequest: {
    NotFound: 'join_request.not_found',
    AlreadyDecided: 'join_request.already_decided',
    OnlyRejectedCanBeUnRejected: 'join_request.only_rejected_can_be_un_rejected',
    PhoneAlreadyInvited: 'join_request.phone_already_invited',
    PhoneAlreadyPending: 'join_request.phone_already_pending',
    AnswerRequired: 'join_request.answer_required',
    AnswerTooLong: 'join_request.answer_too_long',
    AnswerInvalidOption: 'join_request.answer_invalid_option',
    InvalidStatus: 'join_request.invalid_status',
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
  Page: {
    MembersOnly: 'page.members_only',
  },
  Docs: {
    FolderNotFound: 'docs.folder_not_found',
    ParentFolderNotFound: 'docs.parent_folder_not_found',
    DocumentNotFound: 'docs.document_not_found',
  },
  JoinForm: {
    QuestionNotFound: 'join_form.question_not_found',
  },
  Feedback: {
    NotConfigured: 'feedback.not_configured',
    CreationFailed: 'feedback.creation_failed',
  },
  Notification: {
    NotFound: 'notification.not_found',
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
      return "new events can only be saved as active or draft";
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
      return "no spots available for a +1";
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
      return 'link must be a partiful.com url';

    // Phone
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
      return "that number is already in the community — try logging in instead";
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
