import { SegmentedControl } from '@/components/ui/SegmentedControl';
import type { View } from 'react-big-calendar';

interface Props {
  value: View;
  onChange: (view: View) => void;
}

const VIEWS: { value: View; label: string }[] = [
  { value: 'month', label: 'month' },
  { value: 'week', label: 'week' },
  { value: 'day', label: 'day' },
  { value: 'agenda', label: 'list' },
];

export function ViewSwitcher({ value, onChange }: Props) {
  return (
    <SegmentedControl<View>
      name="calendar-view"
      ariaLabel="calendar view"
      options={VIEWS}
      value={value}
      onChange={onChange}
    />
  );
}
