import type { components } from '@/api/types.gen';

type UserOut = components['schemas']['UserOut'];
type RoleOut = components['schemas']['RoleOut'];

export const mockMemberRole: RoleOut = {
  id: 'role-member',
  name: 'member',
  is_default: true,
  permissions: [],
  user_count: 12,
};

export const mockUser: UserOut = {
  id: 'user-self',
  phone_number: '+15555550100',
  display_name: 'mock member',
  email: 'mock@example.com',
  bio: 'just here to verify the ui',
  is_paused: false,
  is_superuser: true,
  login_link_requested: false,
  needs_guidelines_consent: false,
  needs_onboarding: false,
  needs_password_reset: false,
  needs_sms_consent: false,
  photo_updated_at: null,
  profile_photo_url: '',
  roles: [mockMemberRole],
  show_email: true,
  show_phone: true,
  calendar_feed_scope: 'all',
  week_start: 'sunday',
};

export const MOCK_ACCESS_TOKEN = 'mock-access-token';
