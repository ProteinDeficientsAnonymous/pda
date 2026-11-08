import { AxiosError, type AxiosResponse } from 'axios';

export function apiError(status: number, code?: string) {
  return new AxiosError('fail', 'ERR', undefined, undefined, {
    status,
    data: code ? { detail: [{ code, field: null }] } : {},
  } as AxiosResponse);
}
