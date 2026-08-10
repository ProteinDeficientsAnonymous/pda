import { useState } from 'react';
import { toast } from 'sonner';

import {
  DEFAULT_DEV_TEST_USER_PASSWORD,
  type DevTestUserOptions,
  useCreateDevTestUser,
} from '@/api/devTools';
import { useVersion } from '@/api/version';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';
import { Toggle } from '@/components/ui/Toggle';

const DEFAULT_OPTIONS: DevTestUserOptions = {
  firstName: 'Test',
  lastName: 'User',
  password: DEFAULT_DEV_TEST_USER_PASSWORD,
  isMember: true,
  needsOnboarding: false,
  needsPasswordReset: false,
  isPaused: false,
  isArchived: false,
  guidelinesConsent: true,
  smsConsent: true,
  contactPrivacyConsent: true,
};

export function DevTestUserButton() {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  const { data: version } = useVersion();
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<DevTestUserOptions>(DEFAULT_OPTIONS);
  const createUser = useCreateDevTestUser();

  if (!isAuthed || version?.environment === 'production') return null;

  function set<K extends keyof DevTestUserOptions>(key: K, value: DevTestUserOptions[K]) {
    setOptions((prev) => ({ ...prev, [key]: value }));
  }

  async function onCreate() {
    try {
      const user = await createUser.mutateAsync(options);
      toast.success(`created ${user.phone_number} / ${user.password} 🌱`);
      setOpen(false);
    } catch {
      toast.error("couldn't create test user — try again");
    }
  }

  return (
    <>
      <button
        type="button"
        aria-label="dev test users"
        onClick={() => {
          setOpen(true);
        }}
        style={{
          position: 'fixed',
          left: '4rem',
          top: 'calc(2.5rem + env(safe-area-inset-top))',
          zIndex: 30,
          width: '2.5rem',
          height: '2.5rem',
        }}
        className="flex items-center justify-center rounded-full border border-amber-600 bg-amber-100 text-sm font-semibold text-amber-900 shadow-lg transition-colors hover:bg-amber-200"
      >
        🧑
      </button>
      {open ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="dev test users"
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
        >
          <button
            type="button"
            aria-label="close"
            onClick={() => {
              setOpen(false);
            }}
            className="absolute inset-0 cursor-default bg-black/60"
          />
          <div className="bg-surface text-foreground relative flex max-h-[85vh] w-full max-w-sm flex-col rounded-lg p-5 shadow-xl">
            <h2 className="mb-1 text-base font-medium">dev test users</h2>
            <p className="text-muted-foreground mb-4 text-sm">
              creates a user — {version?.environment ?? 'local'} only
            </p>

            <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-1">
              <TextField
                label="first name"
                value={options.firstName}
                onChange={(e) => {
                  set('firstName', e.target.value);
                }}
              />
              <TextField
                label="last name"
                value={options.lastName}
                onChange={(e) => {
                  set('lastName', e.target.value);
                }}
              />
              <TextField
                label="password"
                value={options.password}
                onChange={(e) => {
                  set('password', e.target.value);
                }}
              />
              <div className="flex flex-col gap-1">
                <Toggle
                  label="member"
                  checked={options.isMember}
                  onChange={(v) => {
                    set('isMember', v);
                  }}
                />
                <Toggle
                  label="needs onboarding"
                  checked={options.needsOnboarding}
                  onChange={(v) => {
                    set('needsOnboarding', v);
                  }}
                />
                <Toggle
                  label="needs password reset"
                  checked={options.needsPasswordReset}
                  onChange={(v) => {
                    set('needsPasswordReset', v);
                  }}
                />
                <Toggle
                  label="paused"
                  checked={options.isPaused}
                  onChange={(v) => {
                    set('isPaused', v);
                  }}
                />
                <Toggle
                  label="archived"
                  checked={options.isArchived}
                  onChange={(v) => {
                    set('isArchived', v);
                  }}
                />
                <Toggle
                  label="guidelines consent"
                  checked={options.guidelinesConsent}
                  onChange={(v) => {
                    set('guidelinesConsent', v);
                  }}
                />
                <Toggle
                  label="sms consent"
                  checked={options.smsConsent}
                  onChange={(v) => {
                    set('smsConsent', v);
                  }}
                />
                <Toggle
                  label="contact privacy consent"
                  checked={options.contactPrivacyConsent}
                  onChange={(v) => {
                    set('contactPrivacyConsent', v);
                  }}
                />
              </div>
            </div>

            <div className="mt-4 flex shrink-0 flex-col gap-2">
              <Button
                onClick={() => {
                  void onCreate();
                }}
                disabled={createUser.isPending}
                fullWidth
              >
                {createUser.isPending ? 'creating...' : 'create'}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
