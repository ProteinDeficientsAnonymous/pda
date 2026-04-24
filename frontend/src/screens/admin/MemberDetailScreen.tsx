// Admin detail view for a single member. Pulls the member out of the cached
// list (no dedicated detail endpoint exists on the backend) and lets admins
// edit display name / email / phone + pause/unpause the account.

import { useState, type SyntheticEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { extractApiErrorOr } from '@/api/apiErrors';
import { Button } from '@/components/ui/Button';
import { useConfirm } from '@/components/ui/useConfirm';
import { TextField } from '@/components/ui/TextField';
import { Toggle } from '@/components/ui/Toggle';
import { formatPhone } from '@/utils/formatPhone';
import {
  useArchiveUser,
  useSendMemberMagicLink,
  useUpdateMemberRoles,
  useUpdateUser,
  useUsers,
  type Member,
} from '@/api/users';
import { useRoles } from '@/api/roles';
import { ADMIN_ROLE_NAME } from '@/models/permissions';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { buildMagicLinkUrl, buildSmsHref, buildWelcomeMessage } from '@/utils/welcomeMessage';

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
  const navigate = useNavigate();
  const archive = useArchiveUser();
  const { confirm, element: confirmElement } = useConfirm();

  async function onArchive() {
    const confirmed = await confirm({
      title: 'archive member',
      message: `archive ${member.displayName || formatPhone(member.phoneNumber)}? they'll lose access immediately — you can restore them later by approving a new join request.`,
      confirmLabel: 'archive',
      destructive: true,
    });
    if (!confirmed) return;
    try {
      await archive.mutateAsync(member.id);
      toast.success('member archived ✓');
      void navigate('/admin/members');
    } catch (err) {
      toast.error(extractError(err));
    }
  }

  return (
    <ContentContainer>
      <Link
        to="/admin/members"
        className="mb-4 inline-block text-sm text-neutral-500 hover:underline"
      >
        ← back to members
      </Link>

      <header className="mb-6 flex flex-col items-center gap-3 text-center">
        <MemberAvatar member={member} />
        <div className="flex flex-col items-center gap-1">
          <h1 className="text-2xl font-medium tracking-tight">
            {member.displayName || formatPhone(member.phoneNumber)}
          </h1>
          <p className="text-sm text-neutral-600">{formatPhone(member.phoneNumber)}</p>
          {member.email ? <p className="text-sm text-neutral-600">{member.email}</p> : null}
          {member.isPaused ? (
            <span className="mt-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">
              paused
            </span>
          ) : null}
        </div>
      </header>

      <MemberRolesSection
        key={`${member.id}:${member.roles
          .map((r) => r.id)
          .sort()
          .join(',')}`}
        member={member}
      />

      <MemberMagicLinkSection member={member} />

      {member.bio ? (
        <section className="mb-6 rounded-lg border border-neutral-200 bg-white p-4">
          <h2 className="mb-2 text-xs font-medium tracking-wide text-neutral-500">bio</h2>
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
        <div className="flex justify-between">
          <Button variant="secondary" onClick={() => void onArchive()} disabled={archive.isPending}>
            {archive.isPending ? 'archiving…' : 'archive'}
          </Button>
          <Button
            onClick={() => {
              setEditing(true);
            }}
          >
            edit
          </Button>
        </div>
      )}

      {confirmElement}
    </ContentContainer>
  );
}

function MemberRolesSection({ member }: { member: Member }) {
  const { data: allRoles = [], isPending, isError } = useRoles();
  const updateRoles = useUpdateMemberRoles(member.id);
  const [selected, setSelected] = useState(() => new Set(member.roles.map((r) => r.id)));

  const unchanged =
    selected.size === member.roles.length && member.roles.every((r) => selected.has(r.id));

  async function onSaveRoles() {
    try {
      await updateRoles.mutateAsync([...selected]);
      toast.success('roles updated ✓');
    } catch (e) {
      toast.error(extractError(e));
    }
  }

  if (isPending) {
    return <p className="mb-4 text-sm text-neutral-500">loading roles…</p>;
  }
  if (isError) return null;

  return (
    <section className="mb-4">
      <h2 className="mb-2 text-xs font-medium tracking-wide text-neutral-500">roles</h2>
      <div className="flex flex-col gap-2">
        {allRoles.map((r) => (
          <label key={r.id} className="flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={selected.has(r.id)}
              onChange={(e) => {
                setSelected((prev) => {
                  const next = new Set(prev);
                  if (e.target.checked) next.add(r.id);
                  else next.delete(r.id);
                  return next;
                });
              }}
              className="accent-brand-600 h-4 w-4 cursor-pointer rounded"
            />
            <span>{r.name}</span>
          </label>
        ))}
      </div>
      <Button
        type="button"
        className="mt-2"
        variant="secondary"
        disabled={unchanged || updateRoles.isPending}
        onClick={() => void onSaveRoles()}
      >
        {updateRoles.isPending ? 'saving…' : 'save roles'}
      </Button>
    </section>
  );
}

function MemberMagicLinkSection({ member }: { member: Member }) {
  const magic = useSendMemberMagicLink(member.id);
  const [url, setUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function onGenerate() {
    try {
      const { magicLinkToken } = await magic.mutateAsync();
      setUrl(buildMagicLinkUrl(magicLinkToken));
    } catch (e) {
      toast.error(extractError(e));
    }
  }

  async function onCopy() {
    if (!url) return;
    await navigator.clipboard.writeText(url);
    setCopied(true);
    window.setTimeout(() => {
      setCopied(false);
    }, 2000);
  }

  const welcomeMessage = url ? buildWelcomeMessage(member.displayName, url) : '';
  const smsHref = url ? buildSmsHref(member.phoneNumber, welcomeMessage) : '';

  return (
    <section className="mb-6">
      <h2 className="mb-2 text-xs font-medium tracking-wide text-neutral-500">access</h2>
      {url ? (
        <>
          <div className="mb-2 overflow-x-auto rounded-md bg-neutral-100 px-3 py-2 font-mono text-xs break-all">
            {url}
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="secondary" onClick={() => void onCopy()}>
              {copied ? 'copied ✓' : 'copy link'}
            </Button>
            <a
              href={smsHref}
              className="focus-visible:ring-brand-200 bg-surface text-foreground border-border-strong hover:bg-background inline-flex h-10 items-center justify-center rounded-md border px-4 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none"
            >
              send welcome message
            </a>
          </div>
        </>
      ) : (
        <Button
          type="button"
          variant="secondary"
          disabled={magic.isPending}
          onClick={() => void onGenerate()}
        >
          {magic.isPending ? 'working…' : 'generate magic login link'}
        </Button>
      )}
      <p className="mt-1 text-xs text-neutral-500">
        resets password flow for this member and generates a one-time login url for you to send
        them.
      </p>
    </section>
  );
}

function MemberAvatar({ member }: { member: Member }) {
  const initials = (member.displayName || member.phoneNumber).slice(0, 2).toLowerCase() || '?';
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
  const targetIsAdmin = member.roles.some((r) => r.name === ADMIN_ROLE_NAME && r.isDefault);

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
      className="border-border bg-surface flex flex-col gap-3 rounded-lg border p-4"
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
      <Toggle
        label="pause account"
        checked={isPaused}
        onChange={setIsPaused}
        disabled={targetIsAdmin}
      />
      {targetIsAdmin ? <p className="text-xs text-neutral-500">admins can't be paused</p> : null}

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
  return extractApiErrorOr(err, "couldn't save changes — try again");
}
