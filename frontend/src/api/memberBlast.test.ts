import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { makeQueryClient, queryWrapper } from '@/test/render';
import { reportError } from '@/utils/errorReporter';

import {
  useBlastPreview,
  useMemberBlasts,
  useSendMemberBlast,
  useSendTestBlast,
} from './memberBlast';

vi.mock('@/api/client');
vi.mock('@/utils/errorReporter');

const mockedPost = vi.mocked(apiClient.post);
const mockedGet = vi.mocked(apiClient.get);
const payload = { subject: 'hi', body_html: '<p>hi</p>' };
const BASE = '/api/notifications/email-blasts/';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('blast mutations', () => {
  it.each([
    ['preview', useBlastPreview, `${BASE}preview/`],
    ['test', useSendTestBlast, `${BASE}test/`],
  ] as const)('%s posts the payload and returns the body', async (_, hook, path) => {
    mockedPost.mockResolvedValueOnce({ data: { ok: true } });
    const { result } = renderHook(() => hook(), { wrapper: queryWrapper(makeQueryClient()) });
    await expect(result.current.mutateAsync(payload)).resolves.toEqual({ ok: true });
    expect(mockedPost).toHaveBeenCalledWith(path, payload);
  });

  it('send refreshes the blast history', async () => {
    mockedPost.mockResolvedValueOnce({ data: { status: 'sent' } });
    const qc = makeQueryClient();
    const spy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useSendMemberBlast(), { wrapper: queryWrapper(qc) });
    await result.current.mutateAsync(payload);
    expect(mockedPost).toHaveBeenCalledWith(BASE, payload);
    await waitFor(() => expect(spy).toHaveBeenCalledWith({ queryKey: ['member-blasts'] }));
  });

  it('reports a failed send', async () => {
    mockedPost.mockRejectedValueOnce(new Error('boom'));
    const { result } = renderHook(() => useSendMemberBlast(), {
      wrapper: queryWrapper(makeQueryClient()),
    });
    await expect(result.current.mutateAsync(payload)).rejects.toThrow('boom');
    await waitFor(() => expect(vi.mocked(reportError)).toHaveBeenCalled());
  });
});

describe('useMemberBlasts', () => {
  it('loads the blast history', async () => {
    mockedGet.mockResolvedValueOnce({ data: [{ id: 'b1' }] });
    const { result } = renderHook(() => useMemberBlasts(), {
      wrapper: queryWrapper(makeQueryClient()),
    });
    await waitFor(() => expect(result.current.data).toEqual([{ id: 'b1' }]));
    expect(mockedGet).toHaveBeenCalledWith(BASE);
  });
});
