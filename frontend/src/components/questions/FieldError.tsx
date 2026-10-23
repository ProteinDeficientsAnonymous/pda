export function FieldError({ error }: { error?: string | undefined }) {
  if (!error) return null;
  return (
    <p role="alert" className="text-xs text-red-600">
      {error}
    </p>
  );
}
