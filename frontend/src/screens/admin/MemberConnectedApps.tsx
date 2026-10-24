import { useMemberConnectedApps, useRevokeMemberConnectedApp } from '@/api/connect';
import { useAuthStore } from '@/auth/store';
import { hasPermission, Permission } from '@/models/permissions';
import { ConnectedAppsList } from '@/screens/settings/ConnectedAppsList';

export function MemberConnectedApps({ memberId }: { memberId: string }) {
  const user = useAuthStore((s) => s.user);
  if (!hasPermission(user, Permission.ManageUsers)) return null;
  return <MemberConnectedAppsSection memberId={memberId} />;
}

function MemberConnectedAppsSection({ memberId }: { memberId: string }) {
  const { data, isPending, isError } = useMemberConnectedApps(memberId);
  const revoke = useRevokeMemberConnectedApp(memberId);
  return (
    <section className="border-border bg-surface mb-6 rounded-lg border p-4">
      <h2 className="text-muted mb-2 text-xs font-medium tracking-wide">connected apps</h2>
      <ConnectedAppsList
        apps={data}
        isPending={isPending}
        isError={isError}
        onRevoke={revoke.mutateAsync}
      />
    </section>
  );
}
