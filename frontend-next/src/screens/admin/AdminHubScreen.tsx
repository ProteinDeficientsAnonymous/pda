// Landing for /admin — a menu of admin areas filtered by the current user's
// permissions. Mirrors the flutter admin_screen.dart tile layout.

import { Link } from 'react-router-dom';
import { useAuthStore } from '@/auth/store';
import { Permission, hasPermission, type PermissionKey } from '@/models/permissions';
import { ContentContainer } from '@/screens/public/ContentContainer';

interface Tile {
  to: string;
  label: string;
  description: string;
  perm: PermissionKey;
}

const TILES: Tile[] = [
  {
    to: '/members',
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
    to: '/admin/whatsapp',
    label: 'whatsapp bot',
    description: 'bot connection + group config',
    perm: Permission.ManageWhatsapp,
  },
];

export default function AdminHubScreen() {
  const user = useAuthStore((s) => s.user);
  const visible = TILES.filter((t) => hasPermission(user, t.perm));

  return (
    <ContentContainer>
      <h1 className="mb-6 text-2xl font-medium tracking-tight">admin</h1>
      {visible.length === 0 ? (
        <p className="text-sm text-neutral-500">nothing available to you yet</p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {visible.map((t) => (
            <li key={t.to}>
              <Link
                to={t.to}
                className="flex h-full flex-col gap-1 rounded-lg border border-neutral-200 bg-white p-4 transition-colors hover:bg-neutral-50"
              >
                <span className="text-base font-medium text-neutral-900">{t.label}</span>
                <span className="text-xs text-neutral-500">{t.description}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </ContentContainer>
  );
}
