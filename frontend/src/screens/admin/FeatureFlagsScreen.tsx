import { useFeatureFlags, useSetFeatureFlag } from '@/api/featureFlags';
import { useVersion } from '@/api/version';
import { Toggle } from '@/components/ui/Toggle';
import { Feature, type FeatureFlagKey } from '@/models/featureFlags';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

const FLAG_LABELS: Record<FeatureFlagKey, string> = {
  [Feature.HostAttendanceReport]: 'host attendance report',
  [Feature.AdminAttendanceAnalytics]: 'admin attendance analytics',
};

export default function FeatureFlagsScreen() {
  const { data: flags, isPending, isError } = useFeatureFlags();
  const { data: version } = useVersion();
  const setFlag = useSetFeatureFlag();

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load feature flags — try refreshing" />;

  return (
    <ContentContainer>
      <header className="mb-4">
        <h1 className="mb-1 text-2xl font-medium tracking-tight">feature flags</h1>
        <p className="text-muted text-sm">
          {version ? `environment: ${version.environment}` : 'loading environment…'}
        </p>
      </header>

      <ul className="border-border bg-surface divide-border flex flex-col divide-y rounded-lg border px-3">
        {Object.values(Feature).map((key) => (
          <li key={key}>
            <Toggle
              label={FLAG_LABELS[key]}
              checked={flags[key] ?? false}
              disabled={setFlag.isPending}
              onChange={(enabled) => {
                setFlag.mutate({ key, enabled });
              }}
            />
          </li>
        ))}
      </ul>
    </ContentContainer>
  );
}
