import { apiClient } from './client';

export type GiphySource = 'gif' | 'photo';

export interface GiphyResult {
  id: string;
  title: string;
  previewUrl: string;
  originalUrl: string;
  source: GiphySource;
}

interface GiphySearchResponse {
  results: {
    id: string;
    title: string;
    preview_url: string;
    original_url: string;
    source: GiphySource;
  }[];
}

export async function searchGifs(query: string): Promise<GiphyResult[]> {
  const { data } = await apiClient.get<GiphySearchResponse>('/api/community/giphy/search/', {
    params: query.trim().length > 0 ? { q: query.trim(), limit: 24 } : { limit: 24 },
  });
  return data.results.map((r) => ({
    id: r.id,
    title: r.title,
    previewUrl: r.preview_url,
    originalUrl: r.original_url,
    source: r.source,
  }));
}
