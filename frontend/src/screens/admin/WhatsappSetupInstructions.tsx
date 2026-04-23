import { toast } from 'sonner';

interface Step {
  number: string;
  title: string;
  body: string;
  code?: string;
}

const STEPS: Step[] = [
  {
    number: '1',
    title: 'Get a dedicated phone number',
    body: "The bot needs its own WhatsApp account — use a SIM you don't mind dedicating to this. A cheap prepaid SIM works fine.",
  },
  {
    number: '2',
    title: 'Run the bot',
    body: 'In the whatsapp-bot/ directory:',
    code: 'node index.js',
  },
  {
    number: '3',
    title: 'Scan the QR code',
    body: 'The bot prints a QR code in the terminal on first run. Open WhatsApp on the bot phone → Linked devices → Link a device, then scan it. Credentials are saved to auth_info/ so you only do this once.',
  },
  {
    number: '4',
    title: 'Add the bot to your group',
    body: "Add the bot's phone number to the WhatsApp group as you would any contact.",
  },
  {
    number: '5',
    title: 'Find the group ID',
    body: 'Once connected, the bot logs all joined groups on startup:',
    code: 'Joined groups (copy the JID you want as WHATSAPP_GROUP_ID):\n  120363XXXXXXXXXX@g.us  —  PDA members',
  },
  {
    number: '6',
    title: 'Set a bot secret',
    body: 'Pick any random string as a shared secret — this stops unauthorized callers from posting to your group. Set it as the BOT_SECRET environment variable when running the bot:',
    code: 'BOT_SECRET=your-secret node index.js',
  },
  {
    number: '7',
    title: 'Enter the config here',
    body: 'Fill in the Bot URL (where the bot is reachable from the Django server), the secret, and the group ID above, then hit Save. Use the Refresh button to confirm the bot shows as connected.',
  },
];

export function WhatsappSetupInstructions() {
  return (
    <details className="border-border bg-surface group mb-6 rounded-lg border">
      <summary className="text-foreground flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-medium">
        <span>setup instructions</span>
        <span aria-hidden="true" className="text-muted transition-transform group-open:rotate-180">
          ▾
        </span>
      </summary>
      <div className="border-border border-t px-4 py-4">
        <ol className="flex flex-col gap-4">
          {STEPS.map((step) => (
            <StepRow key={step.number} step={step} />
          ))}
        </ol>
      </div>
    </details>
  );
}

function StepRow({ step }: { step: Step }) {
  return (
    <li className="flex items-start gap-3">
      <span className="bg-surface-dim text-foreground-secondary mt-0.5 flex h-6 w-6 flex-none items-center justify-center rounded-full text-xs font-semibold">
        {step.number}
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <p className="text-foreground text-sm font-semibold">{step.title}</p>
        <p className="text-foreground-secondary text-sm">{step.body}</p>
        {step.code ? <CodeBlock code={step.code} /> : null}
      </div>
    </li>
  );
}

function CodeBlock({ code }: { code: string }) {
  async function onCopy() {
    try {
      await navigator.clipboard.writeText(code);
      toast.success('copied ✓');
    } catch {
      toast.error("couldn't copy — try again");
    }
  }

  return (
    <div className="border-border bg-surface-dim flex items-start gap-2 rounded-md border p-2">
      <pre className="text-foreground flex-1 overflow-x-auto px-1 py-1 font-mono text-xs leading-relaxed">
        {code}
      </pre>
      <button
        type="button"
        onClick={() => void onCopy()}
        className="border-border bg-surface text-foreground-secondary hover:bg-surface-dim flex-none rounded border px-2 py-1 text-xs"
        aria-label="copy to clipboard"
      >
        copy
      </button>
    </div>
  );
}
