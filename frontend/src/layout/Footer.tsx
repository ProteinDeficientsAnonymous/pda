export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-border text-muted border-t px-4 py-6 text-center text-xs">
      © {year} protein deficients anonymous
    </footer>
  );
}
