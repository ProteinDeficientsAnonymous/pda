import { useConnectedApps, useRevokeConnectedApp } from '@/api/connect';

import { ConnectedAppsList } from './ConnectedAppsList';

export function ConnectedAppsSection() {
  const { data, isPending, isError } = useConnectedApps();
  const revoke = useRevokeConnectedApp();
  return (
    <ConnectedAppsList
      apps={data}
      isPending={isPending}
      isError={isError}
      onRevoke={revoke.mutateAsync}
    />
  );
}
