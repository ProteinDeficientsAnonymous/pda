import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { SegmentedControl as SharedSegmentedControl } from '@/components/ui/SegmentedControl';
import { TextField } from '@/components/ui/TextField';
import { useAuthStore } from '@/auth/store';
import { useAccessibilityStore, type ThemeMode, type TextScale } from '@/accessibility/store';
import { ContentContainer } from '@/screens/public/ContentContainer';
import { AvatarUpload } from './AvatarUpload';
import { ChangePasswordDialog } from './ChangePasswordDialog';
import { cn } from '@/utils/cn';

export default function SettingsScreen() {
  const user = useAuthStore((s) => s.user);
  const updateProfile = useAuthStore((s) => s.updateProfile);
  const [pwOpen, setPwOpen] = useState(false);

  const themeMode = useAccessibilityStore((s) => s.themeMode);
  const setThemeMode = useAccessibilityStore((s) => s.setThemeMode);
  const dyslexiaFont = useAccessibilityStore((s) => s.dyslexiaFont);
  const toggleDyslexiaFont = useAccessibilityStore((s) => s.toggleDyslexiaFont);
  const textScale = useAccessibilityStore((s) => s.textScale);
  const setTextScale = useAccessibilityStore((s) => s.setTextScale);

  if (!user) return null;

  return (
    <ContentContainer>
      <h1 className="mb-6 text-2xl font-medium tracking-tight">settings</h1>

      <Section label="profile">
        <AvatarUpload />
        <InlineText
          label="display name"
          value={user.displayName}
          onSave={(v) => updateProfile({ displayName: v })}
        />
        <ReadOnly label="phone number" value={user.phoneNumber} />
        <InlineText
          label="email"
          value={user.email}
          onSave={(v) => updateProfile({ email: v })}
          placeholder="add an email"
        />
      </Section>

      <Section label="security">
        <Button
          variant="secondary"
          onClick={() => {
            setPwOpen(true);
          }}
        >
          change password
        </Button>
      </Section>

      <Section label="privacy">
        <Toggle
          label="show phone on my profile"
          checked={user.showPhone}
          onChange={(v) => updateProfile({ showPhone: v })}
        />
        <Toggle
          label="show email on my profile"
          checked={user.showEmail}
          onChange={(v) => updateProfile({ showEmail: v })}
        />
      </Section>

      <Section label="calendar">
        <WeekStartToggle value={user.weekStart} onChange={(v) => updateProfile({ weekStart: v })} />
      </Section>

      <Section label="accessibility">
        <ThemeToggle value={themeMode} onChange={setThemeMode} />
        <DyslexiaToggle checked={dyslexiaFont} onChange={toggleDyslexiaFont} />
        <TextScaleToggle value={textScale} onChange={setTextScale} />
      </Section>

      <ChangePasswordDialog
        open={pwOpen}
        onClose={() => {
          setPwOpen(false);
        }}
      />
    </ContentContainer>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section className="mb-6 rounded-lg border border-border bg-surface p-4">
      <h2 className="mb-3 text-xs font-medium tracking-wide text-muted uppercase">{label}</h2>
      <div className="flex flex-col gap-4">{children}</div>
    </section>
  );
}

function ReadOnly({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-muted">{label}</div>
      <div className="text-sm text-foreground">{value}</div>
    </div>
  );
}

function InlineText({
  label,
  value,
  onSave,
  placeholder,
}: {
  label: string;
  value: string;
  onSave: (v: string) => Promise<void>;
  placeholder?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);

  async function commit() {
    if (draft.trim() === value) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      await onSave(draft.trim());
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    return (
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs text-muted">{label}</div>
          <div className="text-sm text-foreground">{value || placeholder}</div>
        </div>
        <Button
          variant="ghost"
          onClick={() => {
            setDraft(value);
            setEditing(true);
          }}
          aria-label={`edit ${label}`}
        >
          edit
        </Button>
      </div>
    );
  }

  return (
    <div className="flex items-end gap-2">
      <div className="flex-1">
        <TextField
          label={label}
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
          }}
        />
      </div>
      <Button
        variant="ghost"
        onClick={() => {
          setEditing(false);
        }}
        disabled={saving}
      >
        cancel
      </Button>
      <Button onClick={() => void commit()} disabled={saving}>
        save
      </Button>
    </div>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => Promise<void>;
}) {
  return (
    <label className="flex items-center justify-between gap-3">
      <span className="text-sm text-foreground">{label}</span>
      <span
        className={cn(
          'relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors',
          checked ? 'bg-brand-600' : 'bg-toggle-off',
        )}
      >
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => {
            void onChange(e.target.checked);
          }}
          className="sr-only"
        />
        <span
          aria-hidden="true"
          className={cn(
            'inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform',
            checked ? 'translate-x-5' : 'translate-x-0.5',
          )}
        />
      </span>
    </label>
  );
}

function WeekStartToggle({
  value,
  onChange,
}: {
  value: 'sunday' | 'monday';
  onChange: (v: 'sunday' | 'monday') => Promise<void>;
}) {
  const options: { value: 'sunday' | 'monday'; label: string }[] = [
    { value: 'sunday', label: 'sunday' },
    { value: 'monday', label: 'monday' },
  ];
  return (
    <SegmentedControl
      label="week starts on"
      value={value}
      options={options}
      onChange={(v) => void onChange(v)}
    />
  );
}

function ThemeToggle({
  value,
  onChange,
}: {
  value: ThemeMode;
  onChange: (v: ThemeMode) => void;
}) {
  const options: { value: ThemeMode; label: string }[] = [
    { value: 'system', label: 'system' },
    { value: 'light', label: 'light' },
    { value: 'dark', label: 'dark' },
  ];
  return (
    <SegmentedControl
      label="theme"
      options={options}
      value={value}
      onChange={onChange}
    />
  );
}

function DyslexiaToggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: () => void;
}) {
  const options: { value: 'on' | 'off'; label: string }[] = [
    { value: 'off', label: 'off' },
    { value: 'on', label: 'on' },
  ];
  return (
    <SegmentedControl
      label="dyslexia-friendly font"
      options={options}
      value={checked ? 'on' : 'off'}
      onChange={(v) => {
        if ((v === 'on') !== checked) onChange();
      }}
    />
  );
}

function TextScaleToggle({
  value,
  onChange,
}: {
  value: TextScale;
  onChange: (v: TextScale) => void;
}) {
  const options: { value: TextScale; label: string }[] = [
    { value: 1.0, label: 'normal' },
    { value: 1.15, label: 'medium' },
    { value: 1.3, label: 'large' },
  ];
  return (
    <SegmentedControl
      label="text size"
      options={options}
      value={value}
      onChange={onChange}
    />
  );
}

function SegmentedControl<T extends string | number>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div>
      <div className="mb-2 text-sm text-foreground">{label}</div>
      <SharedSegmentedControl
        name={label}
        ariaLabel={label}
        options={options}
        value={value}
        onChange={onChange}
      />
    </div>
  );
}
