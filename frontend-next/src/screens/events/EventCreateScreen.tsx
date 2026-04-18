import { ContentContainer } from '@/screens/public/ContentContainer';
import { EventForm } from './form/EventForm';

export default function EventCreateScreen() {
  return (
    <ContentContainer>
      <h1 className="mb-6 text-2xl font-medium tracking-tight">new event</h1>
      <EventForm />
    </ContentContainer>
  );
}
