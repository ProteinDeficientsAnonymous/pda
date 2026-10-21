import { apiClient } from './client';

export async function downloadFile(
  path: string,
  filename: string,
  params?: Record<string, string>,
): Promise<void> {
  const { data } = await apiClient.get<Blob>(path, { params, responseType: 'blob' });
  const url = URL.createObjectURL(data);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
