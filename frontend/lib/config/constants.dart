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
}

abstract class JoinRequestStatus {
  static const pending = 'pending';
  static const approved = 'approved';
  static const rejected = 'rejected';
}

abstract class PageVisibility {
  static const public_ = 'public';
  static const membersOnly = 'members_only';
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
}

abstract class RoleName {
  static const admin = 'admin';
}
