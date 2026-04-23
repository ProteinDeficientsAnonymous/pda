// Floating feedback button — bottom-right FAB that opens a card form.
//
// Submits to /api/community/feedback/, which creates a GitHub issue. Shown
// only to authed users; route-aware via useLocation. Copy is all lowercase
// per .claude/rules/ui-copy-tone.md. maxLength caps match the frontend
// input-validation guidance (title 150, description 2000) and stay under
// the backend FieldLimit on FeedbackIn (200 / 10000).

import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { toast } from 'sonner';
import { useSubmitFeedback, type FeedbackType } from '@/api/feedback';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';
import { Textarea } from '@/components/ui/Textarea';

const TITLE_MAX = 150;
const DESCRIPTION_MAX = 2000;

export function FeedbackButton() {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  const user = useAuthStore((s) => s.user);
  const location = useLocation();
  const { mutateAsync, isPending } = useSubmitFeedback();

  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isBug, setIsBug] = useState(false);
  const [isFeature, setIsFeature] = useState(false);
  const [titleError, setTitleError] = useState<string | undefined>(undefined);
  const [descriptionError, setDescriptionError] = useState<string | undefined>(undefined);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') close();
    }
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  if (!isAuthed) return null;

  function close() {
    setOpen(false);
    setTitle('');
    setDescription('');
    setIsBug(false);
    setIsFeature(false);
    setTitleError(undefined);
    setDescriptionError(undefined);
  }

  async function onSubmit(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    const trimmedTitle = title.trim();
    const trimmedDescription = description.trim();
    let hasError = false;
    if (!trimmedTitle) {
      setTitleError('required');
      hasError = true;
    } else {
      setTitleError(undefined);
    }
    if (!trimmedDescription) {
      setDescriptionError('required');
      hasError = true;
    } else {
      setDescriptionError(undefined);
    }
    if (hasError) return;

    const feedbackTypes: FeedbackType[] = [];
    if (isBug) feedbackTypes.push('bug');
    if (isFeature) feedbackTypes.push('feature request');

    try {
      const result = await mutateAsync({
        title: trimmedTitle,
        description: trimmedDescription,
        feedbackTypes,
        metadata: {
          route: location.pathname,
          userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : '',
          userDisplayName: (user?.displayName ?? '').split(' ')[0] ?? '',
          appVersion: '',
        },
      });
      const issueUrl = result.html_url;
      if (issueUrl) {
        toast.success('feedback submitted — thanks! 🌱', {
          action: {
            label: 'view your issue',
            onClick: () => {
              window.open(issueUrl, '_blank', 'noopener,noreferrer');
            },
          },
        });
      } else {
        toast.success('feedback submitted — thanks! 🌱');
      }
      close();
    } catch {
      toast.error("couldn't submit feedback — try again");
    }
  }

  return (
    <>
      <button
        type="button"
        aria-label="send feedback"
        onClick={() => {
          setOpen(true);
        }}
        style={{
          position: 'fixed',
          right: '1rem',
          bottom: 'calc(3.5rem + 1rem + env(safe-area-inset-bottom))',
          zIndex: 30,
          width: '3rem',
          height: '3rem',
        }}
        className="bg-brand-600 hover:bg-brand-700 focus-visible:ring-brand-200 text-brand-on flex items-center justify-center rounded-full text-xl font-semibold shadow-lg transition-colors focus-visible:ring-2 focus-visible:outline-none"
      >
        ?
      </button>
      {open ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="send feedback"
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
        >
          <button
            type="button"
            aria-label="close"
            onClick={close}
            className="absolute inset-0 cursor-default bg-black/60"
          />
          <form
            onSubmit={(e) => {
              void onSubmit(e);
            }}
            className="bg-surface text-foreground relative w-full max-w-md rounded-lg p-5 shadow-xl"
          >
            <h2 className="mb-4 text-base font-medium">send feedback</h2>
            <div className="flex flex-col gap-4">
              <TextField
                label="title"
                value={title}
                onChange={(e) => {
                  setTitle(e.target.value);
                }}
                maxLength={TITLE_MAX}
                error={titleError}
              />
              <Textarea
                label="description"
                value={description}
                onChange={(e) => {
                  setDescription(e.target.value);
                }}
                maxLength={DESCRIPTION_MAX}
                rows={5}
                error={descriptionError}
              />
              <div className="flex flex-col gap-2">
                <label className="text-foreground flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={isBug}
                    onChange={(e) => {
                      setIsBug(e.target.checked);
                    }}
                    className="accent-brand-600 h-4 w-4 cursor-pointer rounded"
                  />
                  bug
                </label>
                <label className="text-foreground flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={isFeature}
                    onChange={(e) => {
                      setIsFeature(e.target.checked);
                    }}
                    className="accent-brand-600 h-4 w-4 cursor-pointer rounded"
                  />
                  feature request
                </label>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="secondary" onClick={close} disabled={isPending}>
                  cancel
                </Button>
                <Button type="submit" disabled={isPending}>
                  {isPending ? 'sending...' : 'submit'}
                </Button>
              </div>
            </div>
          </form>
        </div>
      ) : null}
    </>
  );
}
