abstract class EventType {
  static const official = 'official';
  static const community = 'community';
}

abstract class RsvpStatus {
  static const attending = 'attending';
  static const maybe = 'maybe';
  static const cantGo = 'cant_go';
}

abstract class Permission {
  static const createUser = 'create_user';
  static const manageUsers = 'manage_users';
  static const manageRoles = 'manage_roles';
  static const approveJoinRequests = 'approve_join_requests';
  static const manageEvents = 'manage_events';
  static const editGuidelines = 'edit_guidelines';
  static const manageWhatsapp = 'manage_whatsapp';
  static const editFaq = 'edit_faq';
  static const editHomepage = 'edit_homepage';
  static const editJoinQuestions = 'edit_join_questions';
  static const manageSurveys = 'manage_surveys';
  static const tagOfficialEvent = 'tag_official_event';
  static const manageDocs = 'manage_documents';
}

abstract class JoinRequestStatus {
  static const pending = 'pending';
  static const approved = 'approved';
  static const rejected = 'rejected';
}

abstract class PageVisibility {
  static const public_ = 'public';
  static const membersOnly = 'members_only';
  static const inviteOnly = 'invite_only';
}

/// Combined visibility + event-type choice used in the event form UI.
/// Maps to separate [PageVisibility] and [EventType] values for the API.
abstract class EventVisibilityChoice {
  static const official = 'official';
  static const public_ = 'public';
  static const membersOnly = 'members_only';
  static const inviteOnly = 'invite_only';
}

/// Converts a form [choice] into the `(visibility, eventType)` pair for API submission.
(String visibility, String eventType) visibilityChoiceToFields(String choice) {
  if (choice == EventVisibilityChoice.official) {
    return (PageVisibility.public_, EventType.official);
  }
  return (choice, EventType.community);
}

/// Converts existing event fields back into a single [EventVisibilityChoice] value.
String fieldsToVisibilityChoice(String visibility, String eventType) {
  if (eventType == EventType.official) return EventVisibilityChoice.official;
  return visibility;
}

abstract class FieldType {
  static const text = 'text';
  static const textarea = 'textarea';
  static const select = 'select';
  static const multiselect = 'multiselect';
  static const dropdown = 'dropdown';
  static const number = 'number';
  static const yesNo = 'yes_no';
  static const rating = 'rating';
  static const datetimePoll = 'datetime_poll';
}

abstract class PollAvailability {
  static const yes = 'yes';
  static const maybe = 'maybe';
}

abstract class RoleName {
  static const admin = 'admin';
}

abstract class NotificationType {
  static const eventInvite = 'event_invite';
  static const joinRequest = 'join_request';
  static const cohostAdded = 'cohost_added';
}

abstract class InvitePermission {
  static const allMembers = 'all_members';
  static const coHostsOnly = 'co_hosts_only';
}

/// Field length limits for form validation.
/// Keep in sync with backend/community/_field_limits.py (FieldLimit class).
abstract class FieldLimit {
  static const title = 200;
  static const shortText = 300;
  static const description = 2000;
  static const content = 50000;
  static const url = 500;
  static const displayName = 64;
  static const phone = 20;
  static const password = 128;
  static const slug = 100;
  static const roleName = 50;
  static const optionText = 200;
  static const choice = 20;
  static const botSecret = 256;
  static const paymentHandle = 100;
}

abstract class EventDetailLabel {
  static const when = 'when';
  static const about = 'about';
  static const host = 'host';
  static const coHosts = 'co-hosts';
  static const invited = 'invited';
  static const location = 'location';
  static const links = 'links';
  static const cost = 'cost';
  static const rsvp = 'rsvp';
}
