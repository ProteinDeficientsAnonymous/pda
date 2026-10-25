interface Props {
  label: string;
  description?: string | undefined;
}

export function SectionHeader({ label, description }: Props) {
  return (
    <div className="border-border flex flex-col gap-1 border-t pt-5 first:border-t-0 first:pt-0">
      <h2 className="text-lg font-medium tracking-tight">{label}</h2>
      {description ? (
        <p className="text-foreground-tertiary text-sm whitespace-pre-wrap">{description}</p>
      ) : null}
    </div>
  );
}
