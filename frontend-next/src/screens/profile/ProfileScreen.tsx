// Profile: mostly view-only. Bio is inline-editable via dialog; everything
// else edits from /settings. Logout lives here as the primary destructive
// action (matches profile_screen.dart).

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { useAuthStore } from '@/auth/store';
import { useHasAnyAdminPermission } from '@/auth/useAuth';
import { ContentContainer } from '@/screens/public/ContentContainer';
import { BioEditDialog } from './BioEditDialog';

export default function ProfileScreen() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const isAdmin = useHasAnyAdminPermission();
  const navigate = useNavigate();
  const [bioOpen, setBioOpen] = useState(false);

  if (!user) return null;

  const initials = user.displayName.slice(0, 2).toUpperCase() || '?';
  const photoUrl = user.profilePhotoUrl
    ? user.photoUpdatedAt
      ? `${user.profilePhotoUrl}?v=${encodeURIComponent(user.photoUpdatedAt)}`
      : user.profilePhotoUrl
    : '';

  async function onLogout() {
    await logout();
    void navigate('/', { replace: true });
  }

  return (
    <ContentContainer>
      <header className="flex items-center gap-4">
        {photoUrl ? (
          <img src={photoUrl} alt="" className="h-20 w-20 rounded-full object-cover" />
        ) : (
          <span
            aria-hidden="true"
            className="flex h-20 w-20 items-center justify-center rounded-full bg-neutral-200 text-2xl text-neutral-600"
          >
            {initials}
          </span>
        )}
        <div>
          <h1 className="text-2xl font-medium tracking-tight">{user.displayName}</h1>
          <p className="text-sm text-neutral-500">{user.phoneNumber}</p>
        </div>
      </header>

      <section className="mt-8 rounded-lg border border-neutral-200 bg-white p-4">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-xs font-medium tracking-wide text-neutral-500 uppercase">bio</h2>
          {user.bio ? (
            <Button
              variant="ghost"
              onClick={() => {
                setBioOpen(true);
              }}
              aria-label="edit bio"
            >
              edit
            </Button>
          ) : null}
        </div>
        {user.bio ? (
          <p className="text-sm whitespace-pre-wrap text-neutral-800">{user.bio}</p>
        ) : (
          <Button
            variant="secondary"
            onClick={() => {
              setBioOpen(true);
            }}
          >
            add your bio
          </Button>
        )}
      </section>

      <nav aria-label="account" className="mt-4 flex flex-col gap-2">
        <ProfileLink to="/settings" label="settings" />
        <ProfileLink to="/events/mine" label="my events" />
        {isAdmin ? <ProfileLink to="/admin" label="admin" /> : null}
      </nav>

      <div className="mt-8 flex justify-center">
        <Button variant="secondary" onClick={() => void onLogout()}>
          log out
        </Button>
      </div>

      <BioEditDialog
        open={bioOpen}
        initialValue={user.bio}
        onClose={() => {
          setBioOpen(false);
        }}
      />
    </ContentContainer>
  );
}

function ProfileLink({ to, label }: { to: string; label: string }) {
  return (
    <Link
      to={to}
      className="flex items-center justify-between rounded-lg border border-neutral-200 bg-white px-4 py-3 text-sm hover:bg-neutral-50"
    >
      <span>{label}</span>
      <span aria-hidden="true" className="text-neutral-400">
        →
      </span>
    </Link>
  );
}
