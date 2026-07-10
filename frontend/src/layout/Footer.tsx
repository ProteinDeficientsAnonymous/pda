export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-border bg-surface border-t">
      <div className="mx-auto flex max-w-6xl items-center justify-center px-4 py-4">
        <p className="text-muted text-sm">© {year} protein deficients anonymous</p>
      </div>
    </footer>
  );
}
