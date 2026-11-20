import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiClient } from './client';
import type { components } from './types.gen';

type WireSlot = components['schemas']['PlanningSlotOut'];
type WireAvailability = components['schemas']['AvailabilityOut'];
type WireGrid = components['schemas']['GridOut'];
type WireMySlot = components['schemas']['MySlotOut'];

export type SlotKind = components['schemas']['PlanningSlotKind'];
export type BiannualInterest = components['schemas']['BiannualInterest'];
export type PlanningYear = components['schemas']['PlanningYearOut'];
type EventStatus = components['schemas']['EventStatus'];

export interface PlanningSlot {
  id: string;
  label: string;
  month: number;
  kind: SlotKind;
  order: number;
  eventId: string | null;
  eventSlug: string | null;
  eventStatus: EventStatus | null;
}

interface Availability {
  submitted: boolean;
  biannualInterest: BiannualInterest | null;
  monthlyCount: number;
  slotIds: string[];
  updatedAt: string | null;
}

type AssignmentStatus = components['schemas']['AssignmentStatus'];

export interface Assignment {
  id: string;
  slotId: string;
  userId: string;
  status: AssignmentStatus;
}

export interface MySlot {
  assignmentId: string;
  status: AssignmentStatus;
  year: number;
  slot: PlanningSlot;
  teammates: { name: string; status: AssignmentStatus }[];
  checklistDoneIds: string[];
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

interface AvailabilityInput {
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

function mapMySlot(w: WireMySlot): MySlot {
  return {
    assignmentId: w.assignment_id,
    status: w.status,
    year: w.year,
    slot: mapSlot(w.slot),
    teammates: w.teammates,
    checklistDoneIds: w.checklist_done_ids,
  };
}

function mapAvailability(w: WireAvailability): Availability {
  return {
    submitted: w.submitted,
    biannualInterest: w.biannual_interest,
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
      biannualInterest: p.biannual_interest,
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

// everything under ['planning'] — the grid, my slots and availability all derive from the same rows
export function usePlanningMutation<TVars, TData = void>(
  mutationFn: (vars: TVars) => Promise<TData>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn,
    onSettled: () => qc.invalidateQueries({ queryKey: ['planning'] }),
  });
}

export function useSaveAvailability(year: number) {
  return usePlanningMutation(async (input: AvailabilityInput) => {
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
  });
}

export function useCreateYear() {
  return usePlanningMutation(async (year: number) => {
    const body: components['schemas']['PlanningYearIn'] = { year };
    const { data } = await apiClient.post<PlanningYear>('/api/community/planning/years/', body);
    return data;
  });
}

export function useOpenAvailability(year: number) {
  return usePlanningMutation(async () => {
    const { data } = await apiClient.post<PlanningYear>(
      `/api/community/planning/years/${String(year)}/availability/open/`,
    );
    return data;
  });
}

interface SlotInput {
  label: string;
  month: number;
  kind: SlotKind;
}

export function useCreateSlot(year: number) {
  return usePlanningMutation(async (input: SlotInput) => {
    const body: components['schemas']['PlanningSlotIn'] = input;
    const { data } = await apiClient.post<WireSlot>(
      `/api/community/planning/years/${String(year)}/slots/`,
      body,
    );
    return mapSlot(data);
  });
}

export function useUpdateSlot() {
  return usePlanningMutation(async ({ id, patch }: { id: string; patch: Partial<SlotInput> }) => {
    const body: components['schemas']['PlanningSlotPatchIn'] = patch;
    const { data } = await apiClient.patch<WireSlot>(`/api/community/planning/slots/${id}/`, body);
    return mapSlot(data);
  });
}

export function useDeleteSlot() {
  return usePlanningMutation(async (id: string) => {
    await apiClient.delete(`/api/community/planning/slots/${id}/`);
  });
}

export function usePropose() {
  return usePlanningMutation(async ({ slotId, userId }: { slotId: string; userId: string }) => {
    const body: components['schemas']['ProposeIn'] = { user_id: userId };
    await apiClient.post(`/api/community/planning/slots/${slotId}/assignments/`, body);
  });
}

export function useConfirmPlanner() {
  return usePlanningMutation(async ({ slotId, userId }: { slotId: string; userId: string }) => {
    const body: components['schemas']['ProposeIn'] = { user_id: userId };
    await apiClient.post(`/api/community/planning/slots/${slotId}/assignments/confirm/`, body);
  });
}

export function useWithdraw() {
  return usePlanningMutation(async (assignmentId: string) => {
    await apiClient.delete(`/api/community/planning/assignments/${assignmentId}/`);
  });
}

type ProposalsSent = components['schemas']['ProposalsSentOut'];

export function useSendProposals(year: number) {
  return usePlanningMutation(async () => {
    const { data } = await apiClient.post<ProposalsSent>(
      `/api/community/planning/years/${String(year)}/proposals/send/`,
    );
    return data;
  });
}

export function useMySlots() {
  return useQuery({
    queryKey: ['planning', 'me'],
    queryFn: async () => {
      const { data } = await apiClient.get<WireMySlot[]>('/api/community/planning/me/');
      return data.map(mapMySlot);
    },
  });
}

function useRespond(action: 'commit' | 'decline') {
  return usePlanningMutation(async (assignmentId: string) => {
    await apiClient.post(`/api/community/planning/assignments/${assignmentId}/${action}/`);
  });
}

export function useCommit() {
  return useRespond('commit');
}

export function useDecline() {
  return useRespond('decline');
}

export async function linkSlotEvent(slotId: string, eventId: string): Promise<PlanningSlot> {
  const body: components['schemas']['LinkEventIn'] = { event_id: eventId };
  const { data } = await apiClient.post<WireSlot>(
    `/api/community/planning/slots/${slotId}/event/`,
    body,
  );
  return mapSlot(data);
}
