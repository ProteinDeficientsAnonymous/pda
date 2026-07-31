import type { ReactNode } from 'react';

import { BottomNav } from '@/layout/BottomNav';
import { cn } from '@/utils/cn';

export function AuthLayout({
  title,
  subtitle,
  showBottomNav = false,
  children,
}: {
  title: string;
  subtitle?: string;
  showBottomNav?: boolean;
  children: ReactNode;
}) {
  return (
    <>
      <main
        className={cn(
          'bg-background flex min-h-screen items-center justify-center p-4',
          showBottomNav && 'pb-[calc(3.5rem+env(safe-area-inset-bottom))]',
        )}
      >
        <div className="border-border bg-surface w-full max-w-sm rounded-lg border p-6 shadow-(--shadow-sm)">
          <h1 className="text-foreground text-xl font-medium tracking-tight">{title}</h1>
          {subtitle ? <p className="text-foreground-tertiary mt-1 text-sm">{subtitle}</p> : null}
          <div className="mt-6">{children}</div>
        </div>
      </main>
      {showBottomNav ? <BottomNav /> : null}
    </>
  );
}
