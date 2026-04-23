import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';

export interface VersionInfo {
  commitSha: string;
  commitShaShort: string;
  environment: string;
}

interface WireVersion {
  commit_sha: string;
  commit_sha_short: string;
  environment: string;
}

export function useVersion() {
  return useQuery({
    queryKey: ['version'] as const,
    queryFn: async () => {
      const { data } = await apiClient.get<WireVersion>('/api/community/version/');
      return {
        commitSha: data.commit_sha,
        commitShaShort: data.commit_sha_short,
        environment: data.environment,
      } satisfies VersionInfo;
    },
    staleTime: Infinity,
  });
}
