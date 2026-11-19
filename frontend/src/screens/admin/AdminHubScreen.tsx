import { Link } from 'react-router-dom';

import { useAuthStore } from '@/auth/store';
import {
  canViewPlanning,
  Permission,
  type PermissionRule,
  satisfiesRule,
} from '@/models/permissions';
import { ContentContainer } from '@/screens/public/ContentContainer';

type Tile = PermissionRule & {
  to: string;
  label: string;
  description: string;
};

const TILES: Tile[] = [
  {
    to: '/admin/members',
    label: 'members',
    description: 'create, edit, pause, or reset accounts',
    perm: Permission.ManageUsers,
  },
  {
    to: '/join-requests',
    label: 'join requests',
    description: 'approve or reject incoming applications',
    perm: Permission.ApproveJoinRequests,
  },
  {
    to: '/events/manage',
    label: 'events',
    description: 'review drafts, past, and cancelled events',
    perm: Permission.ManageEvents,
  },
  {
    to: '/admin/flagged-events',
    label: 'flagged events',
    description: 'review and action flags from members',
    perm: Permission.ManageEvents,
  },
  {
    to: '/admin/attendance',
    label: 'attendance',
    description: 'who came to events and when',
    perm: Permission.ManageEvents,
  },
  {
    to: '/admin/surveys',
    label: 'surveys',
    description: 'build and review surveys + polls',
    perm: Permission.ManageSurveys,
  },
  {
    to: '/admin/join-form',
    label: 'join form',
    description: 'edit the questions asked on /join',
    perm: Permission.EditJoinQuestions,
  },
  {
    to: '/admin/event-speech',
    label: 'event speech',
    description: 'edit the speech template and open roles',
    perm: Permission.EditSpeechTemplate,
  },
  {
    to: '/docs',
    label: 'docs',
    description: 'manage the shared document library',
    perm: Permission.ManageDocuments,
  },
  {
    to: '/admin/planning',
    label: 'event planning',
    description: "availability and who's planning what",
    allow: canViewPlanning,
  },
];

export default function AdminHubScreen() {
  const user = useAuthStore((s) => s.user);
  const visible = TILES.filter((t) => satisfiesRule(user, t));

  return (
    <ContentContainer>
      {visible.length === 0 ? (
        <p className="text-muted text-sm">nothing available to you yet</p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {visible.map((t) => (
            <li key={t.to}>
              <Link
                to={t.to}
                className="border-border bg-surface hover:bg-background flex h-full flex-col gap-1 rounded-lg border p-4 transition-colors"
              >
                <span className="text-foreground text-base font-medium">{t.label}</span>
                <span className="text-muted text-xs">{t.description}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </ContentContainer>
  );
}
