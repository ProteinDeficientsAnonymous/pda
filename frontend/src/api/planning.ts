import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiClient } from './client';
import type { components } from './types.gen';

type WireSlot = components['schemas']['PlanningSlotOut'];
type WireAvailability = components['schemas']['AvailabilityOut'];

export type SlotKind = components['schemas']['PlanningSlotKind'];
export type BiannualInterest = components['schemas']['BiannualInterest'];
export type PlanningYear = components['schemas']['PlanningYearOut'];

export interface PlanningSlot {
  id: string;
  label: string;
  month: number;
  kind: SlotKind;
  order: number;
  eventId: string | null;
  eventSlug: string | null;
  eventStatus: string | null;
}

export interface Availability {
  submitted: boolean;
  biannualInterest: BiannualInterest | null;
  monthlyCount: number;
  slotIds: string[];
  updatedAt: string | null;
}

export interface AvailabilityInput {
  slotIds: string[];
  biannualInterest: BiannualInterest;
  monthlyCount: number;
}

function mapSlot(w: WireSlot): PlanningSlot {
  return {
    id: w.id,
    label: w.label,
    month: w.month,
    kind: w.kind,
    order: w.order,
    eventId: w.event_id,
    eventSlug: w.event_slug,
    eventStatus: w.event_status,
  };
}

function toInterest(v: string | null): BiannualInterest | null {
  return v === 'yes' || v === 'maybe' || v === 'no' ? v : null;
}

function mapAvailability(w: WireAvailability): Availability {
  return {
    submitted: w.submitted,
    biannualInterest: toInterest(w.biannual_interest),
    monthlyCount: w.monthly_count,
    slotIds: w.slot_ids,
    updatedAt: w.updated_at,
  };
}

export function usePlanningYears() {
  return useQuery({
    queryKey: ['planning', 'years'],
    queryFn: async () => {
      const { data } = await apiClient.get<PlanningYear[]>('/api/community/planning/years/');
      return data;
    },
  });
}

export function usePlanningSlots(year: number) {
  return useQuery({
    queryKey: ['planning', 'slots', year],
    queryFn: async () => {
      const { data } = await apiClient.get<WireSlot[]>(
        `/api/community/planning/years/${String(year)}/slots/`,
      );
      return data.map(mapSlot);
    },
  });
}

export function useMyAvailability(year: number) {
  return useQuery({
    queryKey: ['planning', 'availability', year],
    queryFn: async () => {
      const { data } = await apiClient.get<WireAvailability>(
        `/api/community/planning/years/${String(year)}/availability/me/`,
      );
      return mapAvailability(data);
    },
  });
}

export function useSaveAvailability(year: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: AvailabilityInput) => {
      const body: components['schemas']['AvailabilityIn'] = {
        slot_ids: input.slotIds,
        biannual_interest: input.biannualInterest,
        monthly_count: input.monthlyCount,
      };
      const { data } = await apiClient.put<WireAvailability>(
        `/api/community/planning/years/${String(year)}/availability/me/`,
        body,
      );
      return mapAvailability(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['planning', 'availability', year] });
    },
  });
}

export function useCreateYear() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (year: number) => {
      const body: components['schemas']['PlanningYearIn'] = { year };
      const { data } = await apiClient.post<PlanningYear>('/api/community/planning/years/', body);
      return data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['planning', 'years'] });
    },
  });
}

export interface SlotInput {
  label: string;
  month: number;
  kind: SlotKind;
}

export function useCreateSlot(year: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: SlotInput) => {
      const body: components['schemas']['PlanningSlotIn'] = input;
      const { data } = await apiClient.post<WireSlot>(
        `/api/community/planning/years/${String(year)}/slots/`,
        body,
      );
      return mapSlot(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['planning', 'slots', year] });
    },
  });
}

export function useUpdateSlot(year: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, patch }: { id: string; patch: Partial<SlotInput> }) => {
      const body: components['schemas']['PlanningSlotPatchIn'] = patch;
      const { data } = await apiClient.patch<WireSlot>(
        `/api/community/planning/slots/${id}/`,
        body,
      );
      return mapSlot(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['planning', 'slots', year] });
    },
  });
}

export function useDeleteSlot(year: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/api/community/planning/slots/${id}/`);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['planning', 'slots', year] });
    },
  });
}
