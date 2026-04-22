// Public member profile — any authed member can view another member's profile.
// Phone/email come pre-redacted from the backend based on the target user's
// show_phone / show_email settings, so we just check truthiness here.

import { useParams } from 'react-router-dom';
import { useMemberProfile, type MemberProfile } from '@/api/users';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

export default function MemberProfileScreen() {
  const { userId = '' } = useParams<{ userId: string }>();
  const { data, isPending, isError } = useMemberProfile(userId);

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load this profile — try again" />;

  return (
    <ContentContainer>
      <header className="flex flex-col items-center gap-3 text-center">
        <Avatar member={data} />
        <h1 className="text-2xl font-medium tracking-tight">{data.displayName || 'member'}</h1>
        <ContactLines member={data} />
      </header>

      {data.bio ? (
        <section className="border-border bg-surface mt-8 rounded-lg border p-4">
          <h2 className="text-muted mb-2 text-xs font-medium tracking-wide">bio</h2>
          <p className="text-foreground text-sm whitespace-pre-wrap">{data.bio}</p>
        </section>
      ) : null}
    </ContentContainer>
  );
}

function Avatar({ member }: { member: MemberProfile }) {
  if (member.profilePhotoUrl) {
    return (
      <img src={member.profilePhotoUrl} alt="" className="h-28 w-28 rounded-full object-cover" />
    );
  }
  const initials = (member.displayName || '?').slice(0, 2).toLowerCase();
  return (
    <span
      aria-hidden="true"
      className="bg-toggle-off text-foreground-secondary flex h-28 w-28 items-center justify-center rounded-full text-3xl"
    >
      {initials}
    </span>
  );
}

function ContactLines({ member }: { member: MemberProfile }) {
  const hasPhone = Boolean(member.phoneNumber);
  const hasEmail = Boolean(member.email);
  if (!hasPhone && !hasEmail) {
    return <p className="text-muted text-sm">contact info hidden</p>;
  }
  return (
    <div className="flex flex-col items-center gap-1">
      {hasPhone ? (
        <a
          href={`sms:${member.phoneNumber}`}
          className="text-foreground-secondary text-sm hover:underline"
        >
          {member.phoneNumber}
        </a>
      ) : null}
      {hasEmail ? (
        <a
          href={`mailto:${member.email}`}
          className="text-foreground-secondary text-sm hover:underline"
        >
          {member.email}
        </a>
      ) : null}
    </div>
  );
}
