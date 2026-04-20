import type { ReactNode } from 'react';

export function AuthLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <main className="bg-background flex min-h-screen items-center justify-center p-4">
      <div className="border-border bg-surface w-full max-w-sm rounded-lg border p-6 shadow-(--shadow-sm)">
        <h1 className="text-foreground text-xl font-medium tracking-tight">{title}</h1>
        {subtitle ? <p className="text-foreground-tertiary mt-1 text-sm">{subtitle}</p> : null}
        <div className="mt-6">{children}</div>
      </div>
    </main>
  );
}
