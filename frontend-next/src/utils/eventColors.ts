export type EventType = 'community' | 'official';
export type Visibility = 'public' | 'members_only' | 'invite_only';
export type Brightness = 'light' | 'dark';

const officialLight = { bg: '#D0E8FF', fg: '#1A3A5C' };
const officialDark = { bg: '#1A3050', fg: '#B0D4FF' };

const publicLight = { bg: '#CCE8E4', fg: '#0A3D35' };
const publicDark = { bg: '#103028', fg: '#A8E0D8' };

const membersOnlyLight = { bg: '#FFE0B2', fg: '#5C3800' };
const membersOnlyDark = { bg: '#3D2810', fg: '#FFD6A0' };

const inviteOnlyLight = { bg: '#E0D0F0', fg: '#2D1A5C' };
const inviteOnlyDark = { bg: '#201040', fg: '#D0B8FF' };

export function getEventColors(
  eventType: EventType,
  visibility: Visibility,
  brightness: Brightness,
): { bg: string; fg: string } {
  if (eventType === 'official') {
    return brightness === 'dark' ? officialDark : officialLight;
  }
  if (visibility === 'invite_only') {
    return brightness === 'dark' ? inviteOnlyDark : inviteOnlyLight;
  }
  if (visibility === 'members_only') {
    return brightness === 'dark' ? membersOnlyDark : membersOnlyLight;
  }
  return brightness === 'dark' ? publicDark : publicLight;
}