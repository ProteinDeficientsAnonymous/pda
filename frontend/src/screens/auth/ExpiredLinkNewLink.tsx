import { useState } from 'react';

import { Button } from '@/components/ui/Button';

import { RequestLoginLinkDialog } from './RequestLoginLinkDialog';

export function ExpiredLinkNewLink() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <p className="text-foreground-tertiary text-sm">
        you haven't set a password yet — grab a fresh link below
      </p>
      <Button
        fullWidth
        className="mt-4"
        onClick={() => {
          setOpen(true);
        }}
      >
        send me a new link
      </Button>
      <RequestLoginLinkDialog
        open={open}
        onClose={() => {
          setOpen(false);
        }}
      />
    </>
  );
}
