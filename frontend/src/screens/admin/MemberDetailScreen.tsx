// Admin detail view for a single member. Pulls the member out of the cached
// list (no dedicated detail endpoint exists on the backend) and lets admins
// edit display name / email / phone + pause/unpause the account.

import { useState, type SyntheticEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { isAxiosError } from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';
import { Toggle } from '@/components/ui/Toggle';
import { useUpdateUser, useUsers, type Member } from '@/api/users';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

export default function MemberDetailScreen() {
  const { id = '' } = useParams<{ id: string }>();
  const { data = [], isPending, isError } = useUsers();

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load members — try refreshing" />;

  const member = data.find((m) => m.id === id);
  if (!member) return <ContentError message="member not found" />;

  return <MemberDetailView member={member} />;
}

function MemberDetailView({ member }: { member: Member }) {
  const [editing, setEditing] = useState(false);

  return (
    <ContentContainer>
      <Link to="/members" className="mb-4 inline-block text-sm text-neutral-500 hover:underline">
        ← back to members
      </Link>

      <header className="mb-6 flex flex-col items-center gap-3 text-center">
        <MemberAvatar member={member} />
        <div className="flex flex-col items-center gap-1">
          <h1 className="text-2xl font-medium tracking-tight">
            {member.displayName || member.phoneNumber}
          </h1>
          <p className="text-sm text-neutral-600">{member.phoneNumber}</p>
          {member.email ? <p className="text-sm text-neutral-600">{member.email}</p> : null}
          {member.isPaused ? (
            <span className="mt-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">
              paused
            </span>
          ) : null}
        </div>
      </header>

      {member.roles.length > 0 ? (
        <section className="mb-4">
          <h2 className="mb-2 text-xs font-medium tracking-wide text-neutral-500 uppercase">
            roles
          </h2>
          <div className="flex flex-wrap gap-1">
            {member.roles.map((r) => (
              <span
                key={r.id}
                className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs text-neutral-700"
              >
                {r.name}
              </span>
            ))}
          </div>
        </section>
      ) : null}

      {member.bio ? (
        <section className="mb-6 rounded-lg border border-neutral-200 bg-white p-4">
          <h2 className="mb-2 text-xs font-medium tracking-wide text-neutral-500 uppercase">bio</h2>
          <p className="text-sm whitespace-pre-wrap text-neutral-800">{member.bio}</p>
        </section>
      ) : null}

      {editing ? (
        <MemberEditForm
          key={member.id}
          member={member}
          onCancel={() => {
            setEditing(false);
          }}
          onSaved={() => {
            setEditing(false);
          }}
        />
      ) : (
        <div className="flex justify-end">
          <Button
            variant="secondary"
            onClick={() => {
              setEditing(true);
            }}
          >
            edit
          </Button>
        </div>
      )}
    </ContentContainer>
  );
}

function MemberAvatar({ member }: { member: Member }) {
  const initials = (member.displayName || member.phoneNumber).slice(0, 2).toUpperCase() || '?';
  if (member.profilePhotoUrl) {
    return (
      <img src={member.profilePhotoUrl} alt="" className="h-28 w-28 rounded-full object-cover" />
    );
  }
  return (
    <span
      aria-hidden="true"
      className="flex h-28 w-28 items-center justify-center rounded-full bg-neutral-200 text-3xl text-neutral-600"
    >
      {initials}
    </span>
  );
}

function MemberEditForm({
  member,
  onCancel,
  onSaved,
}: {
  member: Member;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const update = useUpdateUser(member.id);
  const [displayName, setDisplayName] = useState(member.displayName);
  const [phoneNumber, setPhoneNumber] = useState(member.phoneNumber);
  const [email, setEmail] = useState(member.email);
  const [isPaused, setIsPaused] = useState(member.isPaused);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setError(null);
    const patch: Parameters<typeof update.mutateAsync>[0] = {};
    if (displayName !== member.displayName) patch.displayName = displayName.trim();
    if (phoneNumber !== member.phoneNumber) patch.phoneNumber = phoneNumber.trim();
    if (email !== member.email) patch.email = email.trim();
    if (isPaused !== member.isPaused) patch.isPaused = isPaused;

    if (Object.keys(patch).length === 0) {
      onSaved();
      return;
    }

    try {
      await update.mutateAsync(patch);
      toast.success('member updated ✓');
      onSaved();
    } catch (err) {
      const msg = extractError(err);
      setError(msg);
      toast.error(msg);
    }
  }

  return (
    <form
      onSubmit={(e) => void onSubmit(e)}
      className="flex flex-col gap-3 rounded-lg border border-neutral-200 bg-white p-4"
    >
      <TextField
        label="display name"
        value={displayName}
        maxLength={64}
        onChange={(e) => {
          setDisplayName(e.target.value);
        }}
      />
      <TextField
        label="phone number"
        value={phoneNumber}
        maxLength={20}
        onChange={(e) => {
          setPhoneNumber(e.target.value);
        }}
      />
      <TextField
        label="email"
        type="email"
        value={email}
        maxLength={254}
        onChange={(e) => {
          setEmail(e.target.value);
        }}
      />
      <Toggle label="pause account" checked={isPaused} onChange={setIsPaused} />

      {error ? (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      ) : null}

      <div className="mt-2 flex justify-end gap-2">
        <Button variant="ghost" type="button" onClick={onCancel}>
          cancel
        </Button>
        <Button type="submit" disabled={update.isPending}>
          {update.isPending ? 'saving…' : 'save'}
        </Button>
      </div>
    </form>
  );
}

function extractError(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  return "couldn't save changes — try again";
}
