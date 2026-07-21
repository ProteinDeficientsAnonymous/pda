import type { ReactNode } from 'react';
import { useState } from 'react';

import { type TextScale, type ThemeMode, useAccessibilityStore } from '@/accessibility/store';
import { extractApiErrorOr } from '@/api/apiErrors';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { SegmentedControl as SharedSegmentedControl } from '@/components/ui/SegmentedControl';
import { TextField } from '@/components/ui/TextField';
import { CalendarFeedScope, type CalendarFeedScopeValue } from '@/models/user';
import { ContentContainer } from '@/screens/public/ContentContainer';
import { formatPhone } from '@/utils/formatPhone';
import { displayName, optionalDisplayName } from '@/utils/validators';

import { AvatarUpload } from './AvatarUpload';
import { CalendarFeedSubscription } from './CalendarFeedSubscription';
import { ChangePasswordDialog } from './ChangePasswordDialog';
import { InlineBirthday } from './InlineBirthday';
import { PrivacyToggles } from './PrivacyToggles';

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
          label="first name"
          value={user.firstName}
          onSave={(v) => updateProfile({ firstName: v })}
          required
          validate={displayName}
        />
        <InlineText
          label="last name"
          value={user.lastName}
          onSave={(v) => updateProfile({ lastName: v })}
          placeholder="add a last name"
          validate={optionalDisplayName}
        />
        <ReadOnly label="phone number" value={formatPhone(user.phoneNumber)} />
        <InlineText
          label="email"
          value={user.email}
          onSave={(v) => updateProfile({ email: v })}
          placeholder="add an email"
        />
        <InlineText
          label="pronouns"
          value={user.pronouns}
          onSave={(v) => updateProfile({ pronouns: v })}
          placeholder="add your pronouns"
        />
        <InlineText
          label="nickname"
          value={user.nickname}
          onSave={(v) => updateProfile({ nickname: v })}
          placeholder="add a nickname"
        />
        <InlineBirthday
          label="birthday"
          value={user.birthday}
          onSave={(v) => updateProfile({ birthday: v })}
          placeholder="add your birthday"
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
        <PrivacyToggles user={user} onChange={(patch) => void updateProfile(patch)} />
      </Section>

      <Section label="calendar">
        <WeekStartToggle value={user.weekStart} onChange={(v) => updateProfile({ weekStart: v })} />
        <CalendarFeedScopeToggle
          value={user.calendarFeedScope}
          onChange={(v) => updateProfile({ calendarFeedScope: v })}
        />
        <CalendarFeedSubscription />
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

function Section({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section className="border-border bg-surface mb-6 rounded-lg border p-4">
      <h2 className="text-muted mb-3 text-xs font-medium tracking-wide">{label}</h2>
      <div className="flex flex-col gap-4">{children}</div>
    </section>
  );
}

function ReadOnly({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-muted text-xs">{label}</div>
      <div className="text-foreground text-sm">{value}</div>
    </div>
  );
}

function InlineText({
  label,
  value,
  onSave,
  placeholder,
  required = false,
  validate,
}: {
  label: string;
  value: string;
  onSave: (v: string) => Promise<void>;
  placeholder?: string;
  required?: boolean;
  validate?: (v: string) => string | null;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function commit() {
    if (required && !draft.trim()) {
      setError(`${label} required`);
      return;
    }
    const validationError = validate?.(draft);
    if (validationError) {
      setError(validationError === 'Required' ? `${label} required` : validationError);
      return;
    }
    if (draft.trim() === value) {
      setEditing(false);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSave(draft.trim());
      setEditing(false);
    } catch (err) {
      setError(extractApiErrorOr(err, "couldn't save — try again"));
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    return (
      <div className="flex items-center justify-between">
        <div>
          <div className="text-muted text-xs">{label}</div>
          <div className="text-foreground text-sm">{value || placeholder}</div>
        </div>
        <Button
          variant="ghost"
          onClick={() => {
            setDraft(value);
            setError(null);
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
          error={error ?? undefined}
          onChange={(e) => {
            setDraft(e.target.value);
            if (error) setError(null);
          }}
        />
      </div>
      <Button
        variant="ghost"
        onClick={() => {
          setError(null);
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

function CalendarFeedScopeToggle({
  value,
  onChange,
}: {
  value: CalendarFeedScopeValue;
  onChange: (v: CalendarFeedScopeValue) => Promise<void>;
}) {
  const options: { value: CalendarFeedScopeValue; label: string }[] = [
    { value: CalendarFeedScope.All, label: 'all events' },
    { value: CalendarFeedScope.Mine, label: 'my events' },
  ];
  return (
    <SegmentedControl
      label="calendar feed shows"
      value={value}
      options={options}
      onChange={(v) => void onChange(v)}
    />
  );
}

function ThemeToggle({ value, onChange }: { value: ThemeMode; onChange: (v: ThemeMode) => void }) {
  const options: { value: ThemeMode; label: string }[] = [
    { value: 'system', label: 'system' },
    { value: 'light', label: 'light' },
    { value: 'dark', label: 'dark' },
  ];
  return <SegmentedControl label="theme" options={options} value={value} onChange={onChange} />;
}

function DyslexiaToggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
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
  return <SegmentedControl label="text size" options={options} value={value} onChange={onChange} />;
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
      <div className="text-foreground mb-2 text-sm">{label}</div>
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
