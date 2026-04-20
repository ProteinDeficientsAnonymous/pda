// Profile: mostly view-only. Bio is inline-editable via dialog; everything
// else edits from /settings. Logout lives here as the primary destructive
// action (matches profile_screen.dart).

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { useAuthStore } from '@/auth/store';
import { useHasAnyAdminPermission } from '@/auth/useAuth';
import { ContentContainer } from '@/screens/public/ContentContainer';
import { AvatarUpload } from '@/screens/settings/AvatarUpload';
import { cn } from '@/utils/cn';
import { BioEditDialog } from './BioEditDialog';

export default function ProfileScreen() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const isAdmin = useHasAnyAdminPermission();
  const navigate = useNavigate();
  const [bioOpen, setBioOpen] = useState(false);

  if (!user) return null;

  async function onLogout() {
    await logout();
    void navigate('/', { replace: true });
  }

  return (
    <ContentContainer>
      <header className="flex flex-col items-center gap-3 text-center">
        <AvatarUpload size="lg" />
        <div className="flex flex-col items-center gap-1">
          <h1 className="text-2xl font-medium tracking-tight">{user.displayName}</h1>
          <ContactLine value={user.phoneNumber} visible={user.showPhone} />
          {user.email ? <ContactLine value={user.email} visible={user.showEmail} /> : null}
        </div>
      </header>

      <section className="mt-8 rounded-lg border border-border bg-surface p-4">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-xs font-medium tracking-wide text-muted uppercase">bio</h2>
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
          <p className="text-sm whitespace-pre-wrap text-foreground">{user.bio}</p>
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
        <ProfileLink to={`/members/${user.id}`} label="view profile" />
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

function ContactLine({ value, visible }: { value: string; visible: boolean }) {
  return (
    <p className="flex items-center gap-1.5 text-sm text-muted">
      <span>{value}</span>
      <span
        aria-label={visible ? 'visible to members' : 'hidden from members'}
        title={visible ? 'visible to members' : 'only you can see this'}
        className={cn(
          'inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium',
          visible
            ? 'bg-brand-50 text-brand-700'
            : 'bg-surface-dim text-muted',
        )}
      >
        {visible ? (
          <EyeIcon className="h-3 w-3" />
        ) : (
          <EyeOffIcon className="h-3 w-3" />
        )}
        {visible ? 'visible' : 'hidden'}
      </span>
    </p>
  );
}

function EyeIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M17.94 17.94A10.94 10.94 0 0112 20c-7 0-11-8-11-8a19.8 19.8 0 015.06-5.94M9.9 4.24A10.94 10.94 0 0112 4c7 0 11 8 11 8a19.77 19.77 0 01-3.17 4.19M1 1l22 22" />
      <path d="M14.12 14.12A3 3 0 119.88 9.88" />
    </svg>
  );
}

function ProfileLink({ to, label }: { to: string; label: string }) {
  return (
    <Link
      to={to}
      className="flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-3 text-sm hover:bg-background"
    >
      <span>{label}</span>
      <span aria-hidden="true" className="text-muted-foreground">
        →
      </span>
    </Link>
  );
}
