import type { components } from '@/api/types.gen';

type HomePageOut = components['schemas']['HomePageOut'];
type GuidelinesOut = components['schemas']['GuidelinesOut'];
type VersionOut = components['schemas']['VersionOut'];
type CalendarTokenOut = components['schemas']['CalendarTokenOut'];
type NotificationOut = components['schemas']['NotificationOut'];
type UnreadCountOut = components['schemas']['UnreadCountOut'];
type WelcomeTemplateOut = components['schemas']['WelcomeTemplateOut'];

const nowIso = new Date().toISOString();

// Minimal ProseMirror doc wrapping a single paragraph — enough for the tiptap
// reader to render without choking on an empty doc.
const pmDoc = (text: string) =>
  JSON.stringify({
    type: 'doc',
    content: [{ type: 'paragraph', content: [{ type: 'text', text }] }],
  });

export const mockHome: HomePageOut = {
  content: 'welcome to pda — the protein deficients anonymous community',
  content_html: '<p>welcome to pda — the protein deficients anonymous community</p>',
  content_pm: pmDoc('welcome to pda — the protein deficients anonymous community'),
  updated_at: nowIso,
};

export const mockFaq: GuidelinesOut = {
  content: 'frequently asked questions go here',
  content_html: '<p>frequently asked questions go here</p>',
  content_pm: pmDoc('frequently asked questions go here'),
  updated_at: nowIso,
};

export const mockGuidelines: GuidelinesOut = {
  content: 'be kind, stay plant-based, look out for each other',
  content_html: '<p>be kind, stay plant-based, look out for each other</p>',
  content_pm: pmDoc('be kind, stay plant-based, look out for each other'),
  updated_at: nowIso,
};

export const mockVersion: VersionOut = {
  commit_sha: 'mockmockmockmockmockmockmockmockmockmock',
  commit_sha_short: 'mockmoc',
  environment: 'mock',
};

export const mockCalendarToken: CalendarTokenOut = {
  token: 'mock-calendar-token',
  feed_url: 'https://example.com/api/community/calendar/feed/?token=mock-calendar-token',
};

export const mockWelcomeTemplate: WelcomeTemplateOut = {
  body: 'welcome to the community 🌱',
  updated_at: nowIso,
};

export const mockNotifications: NotificationOut[] = [
  {
    id: 'notif-1',
    notification_type: 'event_reminder',
    event_id: 'event-potluck',
    related_user_id: null,
    message: 'vegan potluck in the park is in 3 days',
    is_read: false,
    created_at: nowIso,
  },
];

export const mockUnreadCount: UnreadCountOut = {
  count: mockNotifications.filter((n) => !n.is_read).length,
};
