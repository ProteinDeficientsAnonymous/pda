import { toast } from 'sonner';

import { Button } from '@/components/ui/Button';

function surveyParticipantUrl(slug: string): string {
  return `${window.location.origin}/surveys/${slug}`;
}

export function SurveyCopyLinkButton({ slug, className }: { slug: string; className?: string }) {
  async function copyLink() {
    try {
      await navigator.clipboard.writeText(surveyParticipantUrl(slug));
      toast.success('link copied');
    } catch {
      toast.error("couldn't copy — try again");
    }
  }

  return (
    <Button
      variant="ghost"
      className={className}
      onClick={() => {
        void copyLink();
      }}
    >
      copy link
    </Button>
  );
}
