import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { createElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { EventStatus, EventType, EventVisibility, InvitePermission } from '@/models/event';
import { makeEvent } from '@/test/fixtures';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/auth/store', () => {
  const state = { status: 'authed', user: { id: 'u-me' } };
  const useAuthStore = vi.fn((selector?: (s: typeof state) => unknown) =>
    selector ? selector(state) : state,
  );
  return { useAuthStore };
});

import { apiClient } from '@/api/client';

import {
  eventToFormValues,
  toPartialWireBody,
  useInviteToEvent,
  useUploadEventPhoto,
} from './eventWrites';
import { textRecipientsKeys } from './textRecipients';

describe('eventToFormValues enum validation', () => {
  it('passes through known enum values', () => {
    const form = eventToFormValues(
      makeEvent({
        eventType: EventType.Official,
        visibility: EventVisibility.MembersOnly,
        invitePermission: InvitePermission.CoHostsOnly,
        status: EventStatus.Cancelled,
      }),
    );
    expect(form.eventType).toBe('official');
    expect(form.visibility).toBe('members_only');
    expect(form.invitePermission).toBe('co_hosts_only');
    expect(form.status).toBe('cancelled');
  });

  it('falls back to safe defaults on unknown enum values', () => {
    const form = eventToFormValues(
      makeEvent({
        eventType: 'galaxy_brain',
        visibility: 'top_secret',
        invitePermission: 'nobody',
        status: 'quantum',
      }),
    );
    expect(form.eventType).toBe(EventType.Community);
    expect(form.visibility).toBe(EventVisibility.Public);
    expect(form.invitePermission).toBe(InvitePermission.AllMembers);
    expect(form.status).toBe(EventStatus.Active);
  });

  it('coerces type and visibility independently', () => {
    const form = eventToFormValues(makeEvent({ eventType: 'bogus', visibility: 'bogus' }));
    expect(form.eventType).toBe('community');
    expect(form.visibility).toBe('public');
  });

  it('maps tags to tagIds', () => {
    const form = eventToFormValues(
      makeEvent({
        tags: [
          { id: 't1', name: 'walk', slug: 'walk' },
          { id: 't2', name: 'restaurant meetup', slug: 'restaurant-meetup' },
        ],
      }),
    );
    expect(form.tagIds).toEqual(['t1', 't2']);
  });
});

describe('toPartialWireBody', () => {
  it('only includes keys present in the partial', () => {
    const body = toPartialWireBody({ title: 'new title' });
    expect(body).toEqual({ title: 'new title' });
  });

  it('keeps meaningful falsy values (false, "", null)', () => {
    const body = toPartialWireBody({ rsvpEnabled: false, price: '', maxAttendees: null });
    expect(body).toEqual({ rsvp_enabled: false, price: '', max_attendees: null });
  });

  it('drops explicitly-undefined keys', () => {
    const body = toPartialWireBody({ title: 'x', description: undefined });
    expect(body).toEqual({ title: 'x' });
  });

  it('sends event_type and visibility as independent wire fields', () => {
    expect(toPartialWireBody({ eventType: 'official', visibility: 'public' })).toEqual({
      event_type: 'official',
      visibility: 'public',
    });
    expect(toPartialWireBody({ visibility: 'invite_only' })).toEqual({
      visibility: 'invite_only',
    });
  });

  it('maps camelCase keys to their snake_case wire keys with transforms', () => {
    const body = toPartialWireBody({ startDatetime: '2026-06-01T00:00:00Z', venmoLink: 'leah' });
    expect(body.start_datetime).toBe('2026-06-01T00:00:00Z');
    // venmoLink is run through toVenmoUrl — the bare handle becomes a full url.
    expect(typeof body.venmo_link).toBe('string');
    expect(body.venmo_link).toContain('leah');
  });

  it('maps tagIds to tag_ids, including an empty list (clears tags)', () => {
    expect(toPartialWireBody({ tagIds: ['t1', 't2'] })).toEqual({ tag_ids: ['t1', 't2'] });
    expect(toPartialWireBody({ tagIds: [] })).toEqual({ tag_ids: [] });
  });
});

describe('useInviteToEvent', () => {
  const EVENT_ID = '11111111-1111-1111-1111-111111111111';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  function buildWrapper() {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const Wrapper = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children);
    return { qc, Wrapper };
  }

  it('invalidates the text-recipients query so the group-text count refreshes (issue 612)', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: EVENT_ID } });
    const { qc, Wrapper } = buildWrapper();
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries');

    const { result } = renderHook(() => useInviteToEvent(EVENT_ID), { wrapper: Wrapper });
    result.current.mutate(['user-a']);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: textRecipientsKeys.detail(EVENT_ID),
    });
  });
});

describe('useUploadEventPhoto', () => {
  const EVENT_ID = '22222222-2222-2222-2222-222222222222';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  function buildWrapper() {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const Wrapper = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children);
    return { qc, Wrapper };
  }

  // Regression for issue 668: on create the id isn't known until create-event
  // resolves, so the upload must use the id from the mutation variables — not
  // an id captured at hook-call time (which was '' on create → 404).
  it('posts to the event id passed at call-time', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: makeEvent({ id: EVENT_ID }) });
    const { Wrapper } = buildWrapper();

    const { result } = renderHook(() => useUploadEventPhoto(), { wrapper: Wrapper });
    result.current.mutate({ eventId: EVENT_ID, blob: new Blob(['x'], { type: 'image/png' }) });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    expect(apiClient.post).toHaveBeenCalledWith(
      `/api/community/events/${EVENT_ID}/photo/`,
      expect.any(FormData),
      expect.objectContaining({ headers: { 'Content-Type': 'multipart/form-data' } }),
    );
  });
});
