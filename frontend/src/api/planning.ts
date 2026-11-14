import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiClient } from './client';
import type { components } from './types.gen';

type WireSlot = components['schemas']['PlanningSlotOut'];
type WireAvailability = components['schemas']['AvailabilityOut'];
type WireGrid = components['schemas']['GridOut'];

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

export type AssignmentStatus = components['schemas']['AssignmentStatus'];

export interface Assignment {
  id: string;
  slotId: string;
  userId: string;
  status: AssignmentStatus;
}

export interface PlannerColumn {
  userId: string;
  name: string;
  isPlanner: boolean;
  hasEmail: boolean;
  submitted: boolean;
  biannualInterest: BiannualInterest | null;
  monthlyCount: number;
  availableSlotIds: string[];
}

export interface PlanningGrid {
  year: number;
  slots: PlanningSlot[];
  planners: PlannerColumn[];
  assignments: Assignment[];
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

function mapGrid(year: number, w: WireGrid): PlanningGrid {
  return {
    year,
    slots: w.slots.map(mapSlot),
    planners: w.planners.map((p) => ({
      userId: p.user_id,
      name: p.name,
      isPlanner: p.is_planner,
      hasEmail: p.has_email,
      submitted: p.submitted,
      biannualInterest: toInterest(p.biannual_interest),
      monthlyCount: p.monthly_count,
      availableSlotIds: p.available_slot_ids,
    })),
    assignments: w.assignments.map((a) => ({
      id: a.id,
      slotId: a.slot_id,
      userId: a.user_id,
      status: a.status,
    })),
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

export function usePlanningGrid(year: number) {
  return useQuery({
    queryKey: ['planning', 'grid', year],
    queryFn: async () => {
      const { data } = await apiClient.get<WireGrid>(
        `/api/community/planning/years/${String(year)}/grid/`,
      );
      return mapGrid(year, data);
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
      void qc.invalidateQueries({ queryKey: ['planning', 'grid', year] });
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
      void qc.invalidateQueries({ queryKey: ['planning', 'grid', year] });
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
      void qc.invalidateQueries({ queryKey: ['planning', 'grid', year] });
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
      void qc.invalidateQueries({ queryKey: ['planning', 'grid', year] });
    },
  });
}
