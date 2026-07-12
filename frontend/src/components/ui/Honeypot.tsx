interface Props {
  value: string;
  onChange: (value: string) => void;
}

export function Honeypot({ value, onChange }: Props) {
  return (
    <div aria-hidden="true" className="absolute -left-[9999px] h-0 w-0 overflow-hidden">
      <label htmlFor="website-hp">website (leave blank)</label>
      <input
        id="website-hp"
        type="text"
        name="website"
        tabIndex={-1}
        autoComplete="off"
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
        }}
      />
    </div>
  );
}
