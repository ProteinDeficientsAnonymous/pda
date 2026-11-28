import { Link } from 'react-router-dom';

import { buttonClass } from '@/components/ui/buttonClass';
import { ContentContainer } from '@/screens/public/ContentContainer';

export function ForbiddenNotice({
  message,
  subtext = 'if you think this is a mistake, reach out to the host',
  loginRedirect,
}: {
  message: string;
  subtext?: string;
  loginRedirect?: string;
}) {
  return (
    <ContentContainer>
      <section className="border-border bg-surface mt-8 rounded-lg border p-6">
        <h2 className="mb-2 text-base font-medium">{message}</h2>
        <p className="text-foreground-tertiary mb-4 text-sm">{subtext}</p>
        <div className="flex flex-wrap gap-3">
          {loginRedirect ? (
            <Link to={`/login?redirect=${loginRedirect}`} className={buttonClass()}>
              log in
            </Link>
          ) : null}
          <Link
            to="/calendar"
            className="border-border-strong text-foreground-secondary hover:bg-background inline-flex h-10 items-center rounded-md border px-4 text-sm font-medium"
          >
            back to calendar
          </Link>
        </div>
      </section>
    </ContentContainer>
  );
}
