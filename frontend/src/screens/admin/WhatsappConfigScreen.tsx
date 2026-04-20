import { useState } from 'react';
import { isAxiosError } from 'axios';
import {
  useUpdateWhatsappConfig,
  useWhatsappConfig,
  useWhatsappStatus,
  type WhatsappConfig,
} from '@/api/whatsapp';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { WhatsappSetupInstructions } from './WhatsappSetupInstructions';

export default function WhatsappConfigScreen() {
  const { data, isPending, isError } = useWhatsappConfig();
  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load whatsapp config" />;
  // Split loading gate + form body so form state seeds lazily from data
  // without a setState-in-effect (the form remounts if the query refetches
  // with a different object identity via keyed mount below).
  return <WhatsappConfigForm config={data} />;
}

function WhatsappConfigForm({ config }: { config: WhatsappConfig }) {
  const { data: connected, isPending: statusPending } = useWhatsappStatus();
  const update = useUpdateWhatsappConfig();

  const [botUrl, setBotUrl] = useState(() => config.botUrl);
  const [groupId, setGroupId] = useState(() => config.groupId);
  const [secret, setSecret] = useState('');
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.SyntheticEvent) {
    e.preventDefault();
    setError(null);
    setSaved(false);
    const patch: Parameters<typeof update.mutateAsync>[0] = {
      botUrl,
      groupId,
    };
    // Only include secret when the admin typed something — otherwise we
    // avoid clobbering the stored value.
    if (secret.trim().length > 0) patch.botSecret = secret;
    try {
      await update.mutateAsync(patch);
      setSecret('');
      setSaved(true);
    } catch (err) {
      setError(extractError(err));
    }
  }

  return (
    <ContentContainer>
      <h1 className="mb-2 text-2xl font-medium tracking-tight">whatsapp config</h1>
      <p className="text-foreground-tertiary mb-6 text-sm">bot connection settings</p>

      <WhatsappSetupInstructions />

      <section className="border-border bg-surface mb-6 flex items-center gap-3 rounded-lg border p-4">
        <StatusDot state={statusPending ? 'checking' : connected ? 'connected' : 'offline'} />
        <span className="text-foreground text-sm">
          {statusPending ? 'checking…' : connected ? 'connected' : 'not reachable'}
        </span>
      </section>

      <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-4">
        <TextField
          label="bot url"
          type="url"
          value={botUrl}
          onChange={(e) => {
            setBotUrl(e.target.value);
          }}
          maxLength={256}
          placeholder="https://whatsapp-bot.example.com"
          hint="external URL the pda server will POST to"
        />
        <TextField
          label="group id"
          value={groupId}
          onChange={(e) => {
            setGroupId(e.target.value);
          }}
          maxLength={256}
          placeholder="1234567890@g.us"
        />
        <TextField
          label="bot secret"
          type="password"
          value={secret}
          onChange={(e) => {
            setSecret(e.target.value);
          }}
          maxLength={256}
          placeholder={config.hasSecret ? '••••••••' : 'not set'}
          hint="leave empty to keep the current secret"
        />

        {error ? (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        ) : null}
        {saved ? <p className="text-sm text-green-700">saved ✓</p> : null}

        <div className="flex justify-end">
          <Button type="submit" disabled={update.isPending}>
            {update.isPending ? 'saving…' : 'save'}
          </Button>
        </div>
      </form>
    </ContentContainer>
  );
}

function StatusDot({ state }: { state: 'connected' | 'offline' | 'checking' }) {
  const color =
    state === 'connected' ? 'bg-green-500' : state === 'offline' ? 'bg-red-500' : 'bg-toggle-off';
  return <span aria-hidden="true" className={`h-2.5 w-2.5 rounded-full ${color}`} />;
}

function extractError(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  return "couldn't save — try again";
}
