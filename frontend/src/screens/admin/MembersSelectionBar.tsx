import { Button } from '@/components/ui/Button';

interface Props {
  count: number;
  onMark: () => void;
  onClear: () => void;
}

export function MembersSelectionBar({ count, onMark, onClear }: Props) {
  if (count === 0) return null;

  return (
    <div className="border-border bg-surface mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3">
      <p className="text-foreground text-sm font-medium">{count} selected</p>
      <div className="flex items-center gap-2">
        <Button variant="secondary" onClick={onClear}>
          clear selection
        </Button>
        <Button onClick={onMark}>mark attended</Button>
      </div>
    </div>
  );
}
