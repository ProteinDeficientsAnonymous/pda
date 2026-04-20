import { cn } from '@/utils/cn';
import { passwordChecks } from './passwordRule';

export function PasswordChecklist({ value }: { value: string }) {
  const checks = passwordChecks(value);
  return (
    <ul aria-label="password requirements" className="flex flex-col gap-1 text-xs">
      {checks.map((c) => (
        <li
          key={c.label}
          className={cn(
            'flex items-center gap-2',
            c.ok ? 'text-positive' : 'text-foreground-secondary',
          )}
        >
          <span aria-hidden="true">{c.ok ? '✓' : '•'}</span>
          <span>{c.label}</span>
        </li>
      ))}
    </ul>
  );
}
