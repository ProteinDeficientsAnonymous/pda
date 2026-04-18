import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';
import { useAuthStore } from '@/auth/store';
import { ContentContainer } from '@/screens/public/ContentContainer';
import { AvatarUpload } from './AvatarUpload';
import { ChangePasswordDialog } from './ChangePasswordDialog';
import { cn } from '@/utils/cn';

export default function SettingsScreen() {
  const user = useAuthStore((s) => s.user);
  const updateProfile = useAuthStore((s) => s.updateProfile);
  const [pwOpen, setPwOpen] = useState(false);

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
    <section className="mb-6 rounded-lg border border-neutral-200 bg-white p-4">
      <h2 className="mb-3 text-xs font-medium tracking-wide text-neutral-500 uppercase">{label}</h2>
      <div className="flex flex-col gap-4">{children}</div>
    </section>
  );
}

function ReadOnly({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-neutral-500">{label}</div>
      <div className="text-sm text-neutral-800">{value}</div>
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
          <div className="text-xs text-neutral-500">{label}</div>
          <div className="text-sm text-neutral-800">{value || placeholder}</div>
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
      <span className="text-sm text-neutral-800">{label}</span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => {
          void onChange(e.target.checked);
        }}
        className="h-5 w-10 cursor-pointer appearance-none rounded-full bg-neutral-300 transition-colors checked:bg-neutral-900"
      />
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
  return (
    <div>
      <div className="mb-2 text-sm text-neutral-800">week starts on</div>
      <div
        role="radiogroup"
        aria-label="week start"
        className="inline-flex rounded-md border border-neutral-300 bg-white p-0.5"
      >
        {(['sunday', 'monday'] as const).map((v) => {
          const active = v === value;
          return (
            <label
              key={v}
              className={cn(
                'inline-flex h-8 cursor-pointer items-center rounded px-3 text-sm transition-colors',
                active ? 'bg-neutral-900 text-white' : 'text-neutral-700 hover:bg-neutral-100',
              )}
            >
              <input
                type="radio"
                name="week-start"
                value={v}
                checked={active}
                onChange={() => {
                  void onChange(v);
                }}
                className="sr-only"
              />
              {v}
            </label>
          );
        })}
      </div>
    </div>
  );
}
