import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { RsvpStatusPicker } from '@/components/ui/RsvpStatusPicker';
import { type Event, type RsvpInputStatus, RsvpStatus } from '@/models/event';

import { PaymentConfirmStep } from './PaymentConfirmStep';
import { RsvpCommentField } from './RsvpCommentField';
import { RsvpQuestionFields } from './RsvpQuestionFields';
import {
  missingRequiredQuestionIds,
  type RsvpAnswerValue,
  type RsvpQuestionDraft,
  rsvpQuestionsApplyToStatus,
} from './rsvpQuestions';
import { usePaymentGate } from './usePaymentGate';

interface ConfirmArgs {
  status: RsvpInputStatus;
  comment?: string;
  hasPlusOne: boolean;
  paidConfirmed?: boolean;
  questionnaireResponses: Record<string, RsvpAnswerValue>;
}

interface Props {
  open: boolean;
  mode: 'create' | 'edit';
  event: Event;
  initialStatus: RsvpInputStatus;
  initialHasPlusOne: boolean;
  allowPlusOnes: boolean;
  allowComment?: boolean;
  atCapacity?: boolean;
  busy?: boolean;
  questions?: readonly RsvpQuestionDraft[];
  initialAnswers?: Readonly<Record<string, RsvpAnswerValue | undefined>>;
  onConfirm: (args: ConfirmArgs) => void;
  onRemove?: (() => void) | undefined;
  onClose: () => void;
}

export function RsvpBox({
  open,
  mode,
  event,
  initialStatus,
  initialHasPlusOne,
  allowPlusOnes,
  allowComment,
  atCapacity = false,
  busy = false,
  questions = [],
  initialAnswers = {},
  onConfirm,
  onRemove,
  onClose,
}: Props) {
  const [status, setStatus] = useState<RsvpInputStatus>(initialStatus);
  const [comment, setComment] = useState('');
  const [hasPlusOne, setHasPlusOne] = useState(initialHasPlusOne);
  const [showPayment, setShowPayment] = useState(false);
  const [answers, setAnswers] = useState<Record<string, RsvpAnswerValue | undefined>>(() => ({
    ...initialAnswers,
  }));
  const [questionErrors, setQuestionErrors] = useState<Record<string, string | undefined>>({});
  const needsPaymentFor = usePaymentGate(event);

  const showComment = allowComment ?? mode === 'create';
  const showPlusOne = allowPlusOnes;
  const joiningWaitlist = status === RsvpStatus.Attending && atCapacity;
  const showQuestions = questions.length > 0 && rsvpQuestionsApplyToStatus(status);

  function filledQuestionnaireResponses(): Record<string, RsvpAnswerValue> {
    const next: Record<string, RsvpAnswerValue> = {};
    if (!showQuestions) return next;
    for (const q of questions) {
      const value = answers[q.id];
      if (value?.trim()) {
        next[q.id] = value;
      }
    }
    return next;
  }

  function submit(paidConfirmed: boolean) {
    const trimmed = comment.trim();
    const args: ConfirmArgs = {
      status,
      hasPlusOne,
      questionnaireResponses: filledQuestionnaireResponses(),
    };
    if (showComment && trimmed) args.comment = trimmed;
    if (paidConfirmed) args.paidConfirmed = true;
    onConfirm(args);
  }

  function confirm() {
    if (showQuestions) {
      const missing = missingRequiredQuestionIds(questions, answers);
      if (missing.length > 0) {
        const next: Record<string, string | undefined> = {};
        for (const id of missing) next[id] = 'required';
        setQuestionErrors(next);
        return;
      }
    }
    setQuestionErrors({});
    if (needsPaymentFor(status)) {
      setShowPayment(true);
      return;
    }
    submit(false);
  }

  return (
    <Dialog open={open} onClose={onClose} title="rsvp">
      {showPayment ? (
        <PaymentConfirmStep
          event={event}
          busy={busy}
          onConfirm={() => {
            submit(true);
          }}
          onBack={() => {
            setShowPayment(false);
          }}
        />
      ) : (
        <div className="flex max-h-[min(70vh,32rem)] flex-col gap-4">
          <RsvpStatusPicker
            value={status}
            onSelect={setStatus}
            disabled={busy}
            labelFor={(s, defaultLabel) =>
              s === RsvpStatus.Attending && atCapacity ? 'join the waitlist' : defaultLabel
            }
          />

          {showPlusOne ? (
            <div className="flex justify-center">
              <Button
                type="button"
                variant={hasPlusOne ? 'primary' : 'secondary'}
                onClick={() => {
                  setHasPlusOne(!hasPlusOne);
                }}
                disabled={busy}
              >
                {hasPlusOne ? 'remove +1' : 'add +1'}
              </Button>
            </div>
          ) : null}

          {showQuestions || showComment ? (
            <div
              data-testid="rsvp-details-scroll"
              className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pe-1"
            >
              {showQuestions ? (
                <RsvpQuestionFields
                  questions={questions}
                  answers={answers}
                  errors={questionErrors}
                  disabled={busy}
                  onChange={(questionId, value) => {
                    setAnswers((prev) => ({ ...prev, [questionId]: value }));
                    setQuestionErrors((prev) => {
                      if (!prev[questionId]) return prev;
                      const { [questionId]: _removed, ...rest } = prev;
                      return rest;
                    });
                  }}
                />
              ) : null}

              {showComment ? <RsvpCommentField value={comment} onChange={setComment} /> : null}
            </div>
          ) : null}

          <div className="border-border flex shrink-0 items-center justify-between gap-2 border-t pt-3">
            {mode === 'edit' && onRemove ? (
              <Button type="button" variant="secondary" onClick={onRemove} disabled={busy}>
                remove rsvp
              </Button>
            ) : (
              <span />
            )}
            <div className="flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={onClose} disabled={busy}>
                cancel
              </Button>
              <Button type="button" onClick={confirm} disabled={busy}>
                {confirmLabel(mode, joiningWaitlist)}
              </Button>
            </div>
          </div>
        </div>
      )}
    </Dialog>
  );
}

function confirmLabel(mode: 'create' | 'edit', joiningWaitlist: boolean): string {
  if (joiningWaitlist) return 'join the waitlist';
  if (mode === 'edit') return 'save';
  return 'confirm';
}
