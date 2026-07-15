import { useMemo, useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import {
  JoinRequestStatus,
  type JoinRequestSummary,
  useDecideJoinRequest,
  useJoinRequests,
  useResendMagicLink,
  useUnrejectJoinRequest,
} from '@/api/join';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { TextField } from '@/components/ui/TextField';
import { useConfirm } from '@/components/ui/useConfirm';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { formatPhone } from '@/utils/formatPhone';

import { ApprovalCredentialsDialog } from './ApprovalCredentialsDialog';
import { type Decision, JoinRequestCard } from './JoinRequestCard';
import { JoinRequestMessageEditors } from './JoinRequestMessageEditors';
import { MembershipPromotionMessageDialog } from './MembershipPromotionMessageDialog';
import { TentativeApprovalMessageDialog } from './TentativeApprovalMessageDialog';

const Filter = {
  ALL: 'all',
  ...JoinRequestStatus,
} as const;
type Filter = (typeof Filter)[keyof typeof Filter];

const FILTERS: { value: Filter; label: string }[] = [
  { value: Filter.ALL, label: 'all' },
  { value: Filter.PENDING, label: 'pending' },
  { value: Filter.TENTATIVE, label: 'tentative' },
  { value: Filter.APPROVED, label: 'approved' },
  { value: Filter.REJECTED, label: 'rejected' },
];

export default function JoinRequestsScreen() {
  const { data = [], isPending, isError } = useJoinRequests();
  const decide = useDecideJoinRequest();
  const unreject = useUnrejectJoinRequest();
  const resend = useResendMagicLink();
  const { confirm, element: confirmElement } = useConfirm();

  const [filter, setFilter] = useState<Filter>(Filter.PENDING);
  const [query, setQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [credsFor, setCredsFor] = useState<{
    fullName: string;
    firstName: string;
    phoneNumber: string;
    magicLinkToken: string;
  } | null>(null);
  const [tentativeMessageFor, setTentativeMessageFor] = useState<{
    fullName: string;
    firstName: string;
    phoneNumber: string;
  } | null>(null);
  const [membershipMessageFor, setMembershipMessageFor] = useState<{
    fullName: string;
    firstName: string;
    phoneNumber: string;
    magicLinkToken: string | null;
  } | null>(null);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rows = data.filter(
      (r) => (filter === Filter.ALL || r.status === filter) && matchesQuery(r, q),
    );
    return [...rows].sort((a, b) => sortKey(b) - sortKey(a));
  }, [data, filter, query]);

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load join requests — try refreshing" />;

  async function decideRequest(request: JoinRequestSummary, decision: Decision) {
    const name = request.fullName || formatPhone(request.phoneNumber);
    const ok = await confirm(confirmPropsForDecision(decision, name));
    if (!ok) return;

    const wireStatus = decision === 'manually_approved' ? JoinRequestStatus.APPROVED : decision;

    setError(null);
    try {
      const result = await decide.mutateAsync({ id: request.id, status: wireStatus });
      if (decision === 'manually_approved') {
        setMembershipMessageFor({
          fullName: result.fullName,
          firstName: result.firstName,
          phoneNumber: result.phoneNumber,
          magicLinkToken: result.magicLinkToken,
        });
      } else if (decision === JoinRequestStatus.APPROVED && result.magicLinkToken) {
        setCredsFor({
          fullName: result.fullName,
          firstName: result.firstName,
          phoneNumber: result.phoneNumber,
          magicLinkToken: result.magicLinkToken,
        });
      } else if (decision === JoinRequestStatus.TENTATIVE) {
        setTentativeMessageFor({
          fullName: result.fullName,
          firstName: result.firstName,
          phoneNumber: result.phoneNumber,
        });
      }
    } catch (err) {
      setError(extractError(err));
    }
  }

  async function unrejectRequest(request: JoinRequestSummary) {
    const name = request.fullName || formatPhone(request.phoneNumber);
    const ok = await confirm({
      title: 'un-reject request',
      message: `un-reject ${name}? this will move them back to pending review.`,
      confirmLabel: 'un-reject',
    });
    if (!ok) return;

    setError(null);
    try {
      await unreject.mutateAsync(request.id);
    } catch (err) {
      setError(extractError(err));
    }
  }

  async function resendWelcome(request: JoinRequestSummary) {
    const name = request.fullName || formatPhone(request.phoneNumber);
    const ok = await confirm({
      title: 're-send welcome',
      message: `re-send welcome to ${name}? this generates a fresh login link and invalidates any earlier link you sent them.`,
      confirmLabel: 're-send',
    });
    if (!ok) return;

    setError(null);
    try {
      const result = await resend.mutateAsync(request.id);
      if (result.magicLinkToken) {
        setCredsFor({
          fullName: result.fullName,
          firstName: result.firstName,
          phoneNumber: result.phoneNumber,
          magicLinkToken: result.magicLinkToken,
        });
      }
    } catch (err) {
      setError(extractError(err));
    }
  }

  return (
    <ContentContainer>
      <h1 className="mb-6 text-2xl font-medium tracking-tight">join requests</h1>

      <JoinRequestMessageEditors />

      <div className="mb-4 flex justify-center">
        <SegmentedControl
          name="join-filter"
          ariaLabel="filter"
          options={FILTERS}
          value={filter}
          onChange={setFilter}
        />
      </div>

      <div className="mb-4">
        <TextField
          label="search"
          placeholder="name, phone, or email"
          value={query}
          maxLength={100}
          onChange={(e) => {
            setQuery(e.target.value);
          }}
        />
      </div>

      <SortHint filter={filter} hasRows={visible.length > 0} />

      {error ? (
        <p role="alert" className="text-destructive mb-3 text-sm">
          {error}
        </p>
      ) : null}

      {visible.length === 0 ? (
        <p className="text-muted text-sm">
          {query.trim() ? 'nothing matches — try a different search' : 'nothing here 🌿'}
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {visible.map((r) => (
            <li key={r.id}>
              <JoinRequestCard
                request={r}
                busy={decide.isPending || unreject.isPending || resend.isPending}
                onDecide={(status) => {
                  void decideRequest(r, status);
                }}
                onUnreject={() => {
                  void unrejectRequest(r);
                }}
                onResend={() => {
                  void resendWelcome(r);
                }}
              />
            </li>
          ))}
        </ul>
      )}

      {credsFor ? (
        <ApprovalCredentialsDialog
          open
          onClose={() => {
            setCredsFor(null);
          }}
          fullName={credsFor.fullName}
          firstName={credsFor.firstName}
          phoneNumber={credsFor.phoneNumber}
          magicLinkToken={credsFor.magicLinkToken}
        />
      ) : null}
      {tentativeMessageFor ? (
        <TentativeApprovalMessageDialog
          open
          onClose={() => {
            setTentativeMessageFor(null);
          }}
          fullName={tentativeMessageFor.fullName}
          firstName={tentativeMessageFor.firstName}
          phoneNumber={tentativeMessageFor.phoneNumber}
        />
      ) : null}
      {membershipMessageFor ? (
        <MembershipPromotionMessageDialog
          open
          onClose={() => {
            setMembershipMessageFor(null);
          }}
          fullName={membershipMessageFor.fullName}
          firstName={membershipMessageFor.firstName}
          phoneNumber={membershipMessageFor.phoneNumber}
          magicLinkToken={membershipMessageFor.magicLinkToken}
        />
      ) : null}
      {confirmElement}
    </ContentContainer>
  );
}

function SortHint({ filter, hasRows }: { filter: Filter; hasRows: boolean }) {
  if (filter === Filter.APPROVED) {
    return (
      <p className="text-muted mb-3 text-xs">
        sorted newest first — approved members show here until 3 days after their first login, then
        this tab clears them out automatically
      </p>
    );
  }
  if (filter === Filter.TENTATIVE) {
    return (
      <p className="text-muted mb-3 text-xs">
        approved once they come to an event — they&rsquo;ll be promoted automatically when checked
        in, or you can approve them manually below
      </p>
    );
  }
  if (!hasRows) return null;
  return <p className="text-muted mb-3 text-xs">sorted newest first</p>;
}

const DECISION_CONFIRM_PROPS: Record<
  Decision,
  { title: string; confirmLabel: string; destructive: boolean; message: (name: string) => string }
> = {
  [JoinRequestStatus.APPROVED]: {
    title: 'approve request',
    confirmLabel: 'approve',
    destructive: false,
    message: (name) =>
      `approve ${name}? once you approve someone you can't un-approve them — are you sure?`,
  },
  manually_approved: {
    title: 'approve request',
    confirmLabel: 'approve',
    destructive: false,
    message: (name) =>
      `approve ${name}? once you approve someone you can't un-approve them — are you sure?`,
  },
  [JoinRequestStatus.TENTATIVE]: {
    title: 'tentatively approve request',
    confirmLabel: 'tentatively approve',
    destructive: false,
    message: (name) =>
      `tentatively approve ${name}? they'll show up in the tentative tab and get promoted once they check in to an event, or you can approve them manually`,
  },
  [JoinRequestStatus.REJECTED]: {
    title: 'reject request',
    confirmLabel: 'reject',
    destructive: true,
    message: (name) =>
      `reject ${name}? once you reject someone you can't un-reject them — are you sure?`,
  },
};

function confirmPropsForDecision(status: Decision, name: string) {
  const props = DECISION_CONFIRM_PROPS[status];
  return {
    title: props.title,
    message: props.message(name),
    confirmLabel: props.confirmLabel,
    destructive: props.destructive,
  };
}

function sortKey(request: JoinRequestSummary): number {
  const stamp = request.approvedAt ?? request.rejectedAt ?? request.submittedAt;
  return new Date(stamp).getTime();
}

function matchesQuery(request: JoinRequestSummary, q: string): boolean {
  if (!q) return true;
  return (
    request.fullName.toLowerCase().includes(q) ||
    request.phoneNumber.toLowerCase().includes(q) ||
    request.email.toLowerCase().includes(q)
  );
}

function extractError(err: unknown): string {
  return extractApiErrorOr(err, "couldn't complete that action — try again");
}
