import { useQuery } from '@tanstack/react-query';

import { apiClient } from './client';
import type { components } from './types.gen';

type WireReserve = components['schemas']['ReserveOut'];

export interface ReserveEntry {
  id: string;
  label: string;
  collected: number;
  paidOut: number;
  facilitatorDrinks: number;
  leftOver: number;
}

export interface Reserve {
  entries: ReserveEntry[];
  updatedAt: Date | null;
}

export function mapReserve(w: WireReserve): Reserve {
  return {
    entries: w.entries.map((e) => ({
      id: e.id,
      label: e.label,
      collected: Number(e.collected),
      paidOut: Number(e.paid_out),
      facilitatorDrinks: Number(e.facilitator_drinks),
      leftOver: Number(e.left_over),
    })),
    updatedAt: w.updated_at ? new Date(w.updated_at) : null,
  };
}

async function fetchReserve(): Promise<Reserve> {
  const { data } = await apiClient.get<WireReserve>('/api/community/reserve/');
  return mapReserve(data);
}

export function useReserve() {
  return useQuery({ queryKey: ['reserve'], queryFn: fetchReserve });
}
