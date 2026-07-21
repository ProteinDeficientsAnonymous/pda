import { apiClient } from './client';

export interface GiphyResult {
  id: string;
  title: string;
  previewUrl: string;
  originalUrl: string;
}

interface GiphySearchResponse {
  results: {
    id: string;
    title: string;
    preview_url: string;
    original_url: string;
  }[];
}

export async function searchGifs(query: string): Promise<GiphyResult[]> {
  if (query.trim().length === 0) return [];
  const { data } = await apiClient.get<GiphySearchResponse>('/api/community/giphy/search/', {
    params: { q: query.trim(), limit: 24 },
  });
  return data.results.map((r) => ({
    id: r.id,
    title: r.title,
    previewUrl: r.preview_url,
    originalUrl: r.original_url,
  }));
}
