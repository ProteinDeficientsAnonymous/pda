// Fixed bottom nav — calendar / my events / +event / members / profile.
//
// Mirrors Flutter's NavigationBar with labelBehavior=alwaysHide: labels are
// visually hidden but present in the accessible name so screen readers can
// announce them. Active state uses a filled icon + dot so the distinction
// survives the color-blind-friendly rule (not color-only).

import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/auth/store';
import { cn } from '@/utils/cn';

export function BottomNav() {
  const navigate = useNavigate();
  const location = useLocation();
  const onEventsAdd = location.pathname === '/events/add';
  const user = useAuthStore((s) => s.user);
  const photoUrl = user?.profilePhotoUrl
    ? user.photoUpdatedAt
      ? `${user.profilePhotoUrl}?v=${encodeURIComponent(user.photoUpdatedAt)}`
      : user.profilePhotoUrl
    : '';

  return (
    <nav
      aria-label="primary"
      className="border-border bg-surface fixed inset-x-0 bottom-0 z-20 border-t pb-[env(safe-area-inset-bottom)]"
    >
      <div className="mx-auto grid h-14 max-w-6xl grid-cols-5">
        <NavItem to="/calendar" label="calendar">
          {({ active }) => <CalendarIcon filled={active} />}
        </NavItem>

        <NavItem to="/events/mine" label="my events">
          {({ active }) => <StarIcon filled={active} />}
        </NavItem>

        <div className="flex items-center justify-center">
          <button
            type="button"
            aria-label="add event"
            title="add event"
            aria-current={onEventsAdd ? 'page' : undefined}
            onClick={() => void navigate('/events/add')}
            className={cn(
              'text-brand-on inline-flex h-11 w-11 items-center justify-center rounded-full shadow transition-colors',
              onEventsAdd ? 'bg-brand-700' : 'bg-brand-600 hover:bg-brand-700',
            )}
          >
            <PlusIcon />
          </button>
        </div>

        <NavItem to="/members" label="members">
          {({ active }) => <MembersIcon filled={active} />}
        </NavItem>

        <NavItem to="/profile" label="profile">
          {({ active }) =>
            photoUrl ? (
              <ProfilePhoto src={photoUrl} active={active} />
            ) : (
              <ProfileIcon filled={active} />
            )
          }
        </NavItem>
      </div>
    </nav>
  );
}

interface NavItemProps {
  to: string;
  label: string;
  children: (state: { active: boolean }) => React.ReactNode;
}

function NavItem({ to, label, children }: NavItemProps) {
  return (
    <NavLink
      to={to}
      end
      aria-label={label}
      className={({ isActive }) =>
        cn(
          'text-muted hover:bg-background flex flex-col items-center justify-center gap-0.5 transition-colors',
          isActive && 'text-brand-700',
        )
      }
    >
      {({ isActive }) => (
        <>
          {children({ active: isActive })}
          <span
            aria-hidden="true"
            className={cn(
              'bg-brand-700 h-1 w-1 rounded-full transition-opacity',
              isActive ? 'opacity-100' : 'opacity-0',
            )}
          />
          <span className="sr-only">{label}</span>
        </>
      )}
    </NavLink>
  );
}

function CalendarIcon({ filled }: { filled: boolean }) {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill={filled ? 'currentColor' : 'none'}
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="3" y="5" width="18" height="16" rx="2" fill={filled ? 'currentColor' : 'none'} />
      <path d="M8 3v4M16 3v4M3 10h18" stroke={filled ? 'white' : 'currentColor'} />
    </svg>
  );
}

function StarIcon({ filled }: { filled: boolean }) {
  // Star reads as "events i've starred / am part of".
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill={filled ? 'currentColor' : 'none'}
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 3l2.7 5.8 6.3.9-4.6 4.4 1.1 6.3L12 17.8 6.5 20.4l1.1-6.3L3 9.7l6.3-.9L12 3z" />
    </svg>
  );
}

function MembersIcon({ filled }: { filled: boolean }) {
  // Two-person silhouette — distinct from the single-person ProfileIcon.
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill={filled ? 'currentColor' : 'none'}
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="9" cy="8" r="3.5" />
      <circle cx="17" cy="9" r="2.5" />
      <path d="M2.5 20c0-3.6 2.9-6.5 6.5-6.5s6.5 2.9 6.5 6.5" />
      <path d="M16 14.5c3 .3 5.5 2.8 5.5 5.5" />
    </svg>
  );
}

function ProfilePhoto({ src, active }: { src: string; active: boolean }) {
  return (
    <img
      src={src}
      alt=""
      aria-hidden="true"
      className={cn(
        'ring-border h-6 w-6 rounded-full object-cover ring-1',
        active && 'ring-brand-700 ring-2',
      )}
    />
  );
}

function ProfileIcon({ filled }: { filled: boolean }) {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill={filled ? 'currentColor' : 'none'}
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}
