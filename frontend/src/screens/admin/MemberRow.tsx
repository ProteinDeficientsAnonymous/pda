import { format } from 'date-fns';
import { Link } from 'react-router-dom';

import type { Member } from '@/api/users';
import { formatPhone } from '@/utils/formatPhone';

export function MemberRow({ member }: { member: Member }) {
  const initials = (member.fullName || member.phoneNumber).slice(0, 2).toLowerCase();

  // Non-members have no detail page, so the row is a plain div, not a link.
  if (!member.isMember) {
    return (
      <div className="border-border bg-surface flex flex-col gap-2 rounded-lg border p-3">
        <MemberRowBody member={member} initials={initials} />
      </div>
    );
  }

  return (
    <Link
      to={`/admin/members/${member.id}`}
      className="border-border bg-surface hover:bg-surface-dim flex flex-col gap-2 rounded-lg border p-3 transition-colors"
    >
      <MemberRowBody member={member} initials={initials} />
    </Link>
  );
}

function MemberRowBody({ member, initials }: { member: Member; initials: string }) {
  const hasTags = !member.isMember || member.roles.length > 0 || member.isPaused;
  return (
    <>
      <div className="flex items-center gap-3">
        {member.profilePhotoUrl ? (
          <img
            src={member.profilePhotoUrl}
            alt=""
            className="h-10 w-10 shrink-0 rounded-full object-cover"
          />
        ) : (
          <span
            aria-hidden="true"
            className="bg-surface-dim text-foreground-secondary flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm"
          >
            {initials || '?'}
          </span>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-foreground truncate text-sm font-medium">
            {member.fullName || formatPhone(member.phoneNumber)}
          </p>
          <p className="text-foreground-tertiary truncate text-xs">
            {formatPhone(member.phoneNumber)}
          </p>
          {member.email ? (
            <p className="text-foreground-tertiary truncate text-xs">
              {member.email.toLowerCase()}
            </p>
          ) : (
            <p className="text-foreground-tertiary/60 truncate text-xs italic">no email</p>
          )}
          <p className="text-foreground-tertiary/80 truncate text-xs">
            {member.lastAttendedAt
              ? `last attended ${format(member.lastAttendedAt, 'MMM d, yyyy').toLowerCase()}`
              : 'never attended'}
          </p>
        </div>
      </div>
      {hasTags ? (
        <div className="flex flex-wrap gap-1 pl-13">
          {member.roles.map((role) => (
            <span
              key={role.id}
              className="bg-surface-dim text-foreground-secondary rounded-full px-2 py-0.5 text-xs"
            >
              {role.name}
            </span>
          ))}
          {member.isPaused ? (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
              paused
            </span>
          ) : null}
          {!member.isMember ? (
            <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs text-sky-800 dark:bg-sky-900/40 dark:text-sky-200">
              non-member
            </span>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
