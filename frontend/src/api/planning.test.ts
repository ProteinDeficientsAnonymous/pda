import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { makeSlot } from '@/test/fixtures';
import { makeQueryClient, queryWrapper } from '@/test/render';

import {
  linkSlotEvent,
  useCommit,
  useCreateSlot,
  useCreateYear,
  useDecline,
  useDeleteSlot,
  useMyAvailability,
  useMySlots,
  usePlanningGrid,
  usePlanningSlots,
  usePlanningYears,
  usePropose,
  useSaveAvailability,
  useSendProposals,
  useUpdateSlot,
  useWithdraw,
} from './planning';

vi.mock('@/api/client');

beforeEach(() => {
  vi.clearAllMocks();
});

function renderMutation<TVars>(useHook: () => { mutateAsync: (vars: TVars) => Promise<unknown> }) {
  const qc = makeQueryClient();
  const invalidate = vi.spyOn(qc, 'invalidateQueries');
  const { result } = renderHook(useHook, { wrapper: queryWrapper(qc) });
  return { run: (vars: TVars) => result.current.mutateAsync(vars), invalidate };
}

describe('planning mutations', () => {
  it('propose refreshes every planning query, my slots included', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: null });
    const { run, invalidate } = renderMutation(usePropose);
    await run({ slotId: 's1', userId: 'u1' });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['planning'] });
  });

  it('withdraw refreshes every planning query, even when the request fails', async () => {
    vi.mocked(apiClient.delete).mockRejectedValue(new Error('nope'));
    const { run, invalidate } = renderMutation(useWithdraw);
    await expect(run('a1')).rejects.toThrow('nope');
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['planning'] });
  });

  it('finishes invalidating before mutateAsync resolves', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: 'y', year: 2028 } });
    const { run, invalidate } = renderMutation(useCreateYear);
    let invalidated = false;
    invalidate.mockImplementation(async () => {
      await Promise.resolve();
      invalidated = true;
    });
    await run(2028);
    expect(invalidated).toBe(true);
  });
});

const wireSlot = {
  id: 's1',
  label: 'march',
  month: 3,
  kind: 'monthly',
  order: 3,
  event_id: null,
  event_slug: null,
  event_status: null,
};

function renderQuery<T>(useHook: () => { isSuccess: boolean; data: T | undefined }) {
  return renderHook(useHook, { wrapper: queryWrapper() });
}

describe('planning queries', () => {
  it('lists years as returned', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [{ id: 'y', year: 2027 }] });
    const { result } = renderQuery(usePlanningYears);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([{ id: 'y', year: 2027 }]);
  });

  it('maps slots to camelCase', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [wireSlot] });
    const { result } = renderQuery(() => usePlanningSlots(2027));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.get).toHaveBeenCalledWith('/api/community/planning/years/2027/slots/');
    expect(result.current.data).toEqual([makeSlot()]);
  });

  it('maps the grid', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        slots: [wireSlot],
        planners: [
          {
            user_id: 'u1',
            name: 'sam',
            is_planner: true,
            has_email: false,
            submitted: true,
            biannual_interest: 'maybe',
            monthly_count: 2,
            available_slot_ids: ['s1'],
          },
        ],
        assignments: [{ id: 'a1', slot_id: 's1', user_id: 'u1', status: 'proposed' }],
      },
    });
    const { result } = renderQuery(() => usePlanningGrid(2027));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({
      year: 2027,
      slots: [makeSlot()],
      planners: [
        {
          userId: 'u1',
          name: 'sam',
          isPlanner: true,
          hasEmail: false,
          submitted: true,
          biannualInterest: 'maybe',
          monthlyCount: 2,
          availableSlotIds: ['s1'],
        },
      ],
      assignments: [{ id: 'a1', slotId: 's1', userId: 'u1', status: 'proposed' }],
    });
  });

  it('maps my availability', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        submitted: true,
        biannual_interest: 'yes',
        monthly_count: 1,
        slot_ids: ['s1'],
        updated_at: '2027-01-02T00:00:00Z',
      },
    });
    const { result } = renderQuery(() => useMyAvailability(2027));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({
      submitted: true,
      biannualInterest: 'yes',
      monthlyCount: 1,
      slotIds: ['s1'],
      updatedAt: '2027-01-02T00:00:00Z',
    });
  });

  it('maps my slots with their nested slot', async () => {
    const teammates = [{ name: 'alex', status: 'committed' }];
    vi.mocked(apiClient.get).mockResolvedValue({
      data: [{ assignment_id: 'a1', status: 'proposed', year: 2027, slot: wireSlot, teammates }],
    });
    const { result } = renderQuery(useMySlots);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([
      { assignmentId: 'a1', status: 'proposed', year: 2027, slot: makeSlot(), teammates },
    ]);
  });
});

describe('planning writes', () => {
  it('saves availability with snake_case fields', async () => {
    vi.mocked(apiClient.put).mockResolvedValue({
      data: {
        submitted: true,
        biannual_interest: 'no',
        monthly_count: 0,
        slot_ids: [],
        updated_at: null,
      },
    });
    const { run } = renderMutation(() => useSaveAvailability(2027));
    await run({ slotIds: ['s1'], biannualInterest: 'no', monthlyCount: 0 });
    expect(apiClient.put).toHaveBeenCalledWith(
      '/api/community/planning/years/2027/availability/me/',
      {
        slot_ids: ['s1'],
        biannual_interest: 'no',
        monthly_count: 0,
      },
    );
  });

  it('creates, updates and deletes slots', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: wireSlot });
    vi.mocked(apiClient.patch).mockResolvedValue({ data: wireSlot });
    vi.mocked(apiClient.delete).mockResolvedValue({ data: null });
    const input = { label: 'march', month: 3, kind: 'monthly' as const };
    await expect(renderMutation(() => useCreateSlot(2027)).run(input)).resolves.toEqual(makeSlot());
    expect(apiClient.post).toHaveBeenCalledWith('/api/community/planning/years/2027/slots/', input);
    await renderMutation(useUpdateSlot).run({ id: 's1', patch: { label: 'march walk' } });
    expect(apiClient.patch).toHaveBeenCalledWith('/api/community/planning/slots/s1/', {
      label: 'march walk',
    });
    await renderMutation(useDeleteSlot).run('s1');
    expect(apiClient.delete).toHaveBeenCalledWith('/api/community/planning/slots/s1/');
  });

  it.each([
    ['commit', useCommit],
    ['decline', useDecline],
  ] as const)('posts %s to the assignment', async (action, useHook) => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: null });
    await renderMutation(useHook).run('a1');
    expect(apiClient.post).toHaveBeenCalledWith(
      `/api/community/planning/assignments/a1/${action}/`,
    );
  });

  it("sends the year's draft proposals", async () => {
    const sent = { planners_notified: 2, proposals_sent: 3 };
    vi.mocked(apiClient.post).mockResolvedValue({ data: sent });
    await expect(renderMutation(() => useSendProposals(2027)).run(undefined)).resolves.toEqual(
      sent,
    );
    expect(apiClient.post).toHaveBeenCalledWith(
      '/api/community/planning/years/2027/proposals/send/',
    );
  });

  it('links a slot to an event', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { ...wireSlot, event_id: 'e1', event_slug: 'march-walk', event_status: 'active' },
    });
    await expect(linkSlotEvent('s1', 'e1')).resolves.toEqual(
      makeSlot({ eventId: 'e1', eventSlug: 'march-walk', eventStatus: 'active' }),
    );
    expect(apiClient.post).toHaveBeenCalledWith('/api/community/planning/slots/s1/event/', {
      event_id: 'e1',
    });
  });
});
