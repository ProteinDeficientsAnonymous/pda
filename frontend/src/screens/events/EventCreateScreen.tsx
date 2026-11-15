import { useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';

import { linkSlotEvent, usePlanningSlots } from '@/api/planning';
import { useHasPermission } from '@/auth/useAuth';
import { type Event, EventType } from '@/models/event';
import { Permission } from '@/models/permissions';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { EventForm } from './form/EventForm';

const LINK_FAILED = "event saved, but couldn't link it to the planning slot";
const SLOT_ERROR = "couldn't load that planning slot — try again from the planning page";
const SLOT_START_HOUR = 10;

function slotStart(year: number, month: number): string {
  const now = new Date();
  const monthStart = new Date(year, month - 1, 1, SLOT_START_HOUR);
  const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, SLOT_START_HOUR);
  return (monthStart > tomorrow ? monthStart : tomorrow).toISOString();
}

function PlanningSlotEventForm({ slotId, year }: { slotId: string; year: number }) {
  const qc = useQueryClient();
  const canTagOfficial = useHasPermission(Permission.TagOfficialEvent);
  const { data: slots, isPending, isError } = usePlanningSlots(year);
  if (isPending) return <ContentLoading />;
  const slot = slots?.find((s) => s.id === slotId);
  if (isError || !slot) return <ContentError message={SLOT_ERROR} />;
  if (slot.eventId) return <ContentError message="that slot already has an event" />;

  async function onCreated(event: Event) {
    try {
      await linkSlotEvent(slotId, event.id);
      void qc.invalidateQueries({ queryKey: ['planning'] });
    } catch {
      toast.error(LINK_FAILED);
    }
  }

  return (
    <EventForm
      initial={{
        title: slot.label,
        ...(canTagOfficial ? { eventType: EventType.Official } : {}),
        startDatetime: slotStart(year, slot.month),
      }}
      onCreated={onCreated}
    />
  );
}

function createBody(slotId: string | null, year: number) {
  if (slotId === null) return <EventForm />;
  if (!Number.isInteger(year) || year <= 0) return <ContentError message={SLOT_ERROR} />;
  return <PlanningSlotEventForm slotId={slotId} year={year} />;
}

export default function EventCreateScreen() {
  const [params] = useSearchParams();
  const slotId = params.get('planningSlot');
  const year = Number(params.get('year'));
  return (
    <main className="bg-background min-h-full">
      <div className="mx-auto max-w-6xl px-4 py-8">{createBody(slotId, year)}</div>
    </main>
  );
}
