import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { type DirectoryMember, useMembersDirectory } from '@/api/users';
import { TextField } from '@/components/ui/TextField';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { formatPhone } from '@/utils/formatPhone';

export default function MembersDirectoryScreen() {
  const { data = [], isPending, isError } = useMembersDirectory();
  const [query, setQuery] = useState('');

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return data;
    return data.filter(
      (m) =>
        m.fullName.toLowerCase().includes(q) ||
        m.phoneNumber.toLowerCase().includes(q) ||
        m.email.toLowerCase().includes(q),
    );
  }, [data, query]);

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load members — try refreshing" />;

  return (
    <ContentContainer className="pt-4 md:pt-6">
      <div className="mb-4">
        <TextField
          label="search"
          hideLabel
          placeholder="search name, email, or phone"
          value={query}
          maxLength={100}
          onChange={(e) => {
            setQuery(e.target.value);
          }}
        />
      </div>

      {visible.length === 0 ? (
        <p className="text-muted text-sm">
          {data.length === 0 ? 'no members yet 🌿' : `no one matches "${query}" 🌿`}
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {visible.map((m) => (
            <li key={m.id}>
              <DirectoryRow member={m} />
            </li>
          ))}
        </ul>
      )}
    </ContentContainer>
  );
}

function DirectoryRow({ member }: { member: DirectoryMember }) {
  const initials = (member.fullName || '?').slice(0, 2).toLowerCase();
  return (
    <Link
      to={`/members/${member.id}`}
      className="border-border bg-surface hover:bg-surface-dim flex items-center gap-3 rounded-lg border p-3 transition-colors"
    >
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
          {initials}
        </span>
      )}
      <div className="min-w-0 flex-1">
        <p className="text-foreground truncate text-sm font-medium">
          {member.fullName || 'member'}
        </p>
        {member.phoneNumber || member.email ? (
          <p className="text-foreground-tertiary truncate text-xs">
            {member.phoneNumber ? formatPhone(member.phoneNumber) : member.email}
          </p>
        ) : null}
      </div>
    </Link>
  );
}
