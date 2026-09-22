import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type * as EventWritesModule from '@/api/eventWrites';
import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';
import { makeEvent, makeUser } from '@/test/fixtures';

type EventWrites = typeof EventWritesModule;

const { createEvent, updateEvent } = vi.hoisted(() => ({
  createEvent: vi.fn(),
  updateEvent: vi.fn(),
}));

vi.mock('@/api/eventWrites', async () => {
  const actual = await vi.importActual<EventWrites>('@/api/eventWrites');
  return {
    ...actual,
    useCreateEvent: () => ({ mutateAsync: createEvent, isPending: false }),
    useUpdateEvent: () => ({ mutateAsync: updateEvent, isPending: false }),
    useUploadEventPhoto: () => ({ mutateAsync: vi.fn(), isPending: false }),
  };
});

vi.mock('./EventFormPhoto', () => ({ EventFormPhoto: () => null }));

import { EventForm } from './EventForm';

function renderForm(existing?: Event) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const { container } = render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <EventForm existing={existing} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  const form = container.querySelector<HTMLFormElement>('form')!;
  const onSubmit = vi.fn();
  form.addEventListener('submit', onSubmit);
  return { form, onSubmit };
}

function keydownEnter(target: Element) {
  const event = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true });
  target.dispatchEvent(event);
  return event;
}

// jsdom never implicit-submits on Enter, so replay the browser's default unless the keydown was cancelled.
// Wrapped in act() so submit-handler state updates (dialog save/error) are flushed before assertions.
function pressEnter(target: Element, form: HTMLFormElement) {
  const event = keydownEnter(target);
  if (!event.defaultPrevented) {
    act(() => {
      form.requestSubmit();
    });
  }
  return event;
}

describe('EventForm enter handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    createEvent.mockReturnValue(new Promise(() => {}));
    updateEvent.mockReturnValue(new Promise(() => {}));
    useAuthStore.setState({
      user: makeUser({ id: 'host', fullName: 'host person', phoneNumber: '+15551110000' }),
      status: 'authed',
    });
  });

  it('enter in a text input does not submit or create the event', () => {
    const { form, onSubmit } = renderForm();
    fireEvent.change(screen.getByLabelText('title'), { target: { value: 'beach day' } });
    fireEvent.click(screen.getByRole('switch'));

    pressEnter(screen.getByLabelText('title'), form);

    expect(onSubmit).not.toHaveBeenCalled();
    expect(createEvent).not.toHaveBeenCalled();
  });

  it('enter in the date/time picker time input does not submit', () => {
    const { form, onSubmit } = renderForm();
    fireEvent.change(screen.getByLabelText('title'), { target: { value: 'beach day' } });
    fireEvent.click(screen.getAllByRole('button', { name: 'pick a date & time' })[0]!);

    pressEnter(screen.getByLabelText('time'), form);

    expect(onSubmit).not.toHaveBeenCalled();
    expect(createEvent).not.toHaveBeenCalled();
  });

  it('enter in a textarea is not blocked so the newline still inserts', () => {
    const { onSubmit } = renderForm();

    const event = keydownEnter(screen.getByLabelText('description'));

    expect(event.defaultPrevented).toBe(false);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('enter on buttons is not blocked so they still activate', () => {
    const { onSubmit } = renderForm();
    fireEvent.click(screen.getAllByRole('button', { name: 'pick a date & time' })[0]!);
    const dayCell = document.querySelector('.rdp-day_button');
    expect(dayCell).not.toBeNull();

    for (const target of [screen.getByRole('button', { name: 'publish' }), dayCell!]) {
      expect(keydownEnter(target).defaultPrevented).toBe(false);
    }
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('enter in a select does not submit', () => {
    const { form, onSubmit } = renderForm();

    pressEnter(screen.getByLabelText('who can see it'), form);

    expect(onSubmit).not.toHaveBeenCalled();
    expect(createEvent).not.toHaveBeenCalled();
  });

  it('enter during ime composition is left to the ime', () => {
    const { onSubmit } = renderForm();
    const event = new KeyboardEvent('keydown', {
      key: 'Enter',
      bubbles: true,
      cancelable: true,
      isComposing: true,
    });
    screen.getByLabelText('title').dispatchEvent(event);

    expect(event.defaultPrevented).toBe(false);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('enter with the legacy ime keyCode 229 marker is left to the ime', () => {
    const { onSubmit } = renderForm();

    // Sanity: a plain Enter in an input is still blocked by the guard.
    expect(keydownEnter(screen.getByLabelText('title')).defaultPrevented).toBe(true);

    const event = new KeyboardEvent('keydown', {
      key: 'Enter',
      bubbles: true,
      cancelable: true,
      isComposing: false,
    });
    // KeyboardEventInit lacks keyCode, so set the old-WebKit 229 marker directly.
    Object.defineProperty(event, 'keyCode', { value: 229 });
    screen.getByLabelText('title').dispatchEvent(event);

    // 229 is treated as composing, so the guard keeps its hands off.
    expect(event.defaultPrevented).toBe(false);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('enter in the nested question dialog still saves there without submitting the outer form', () => {
    const { onSubmit } = renderForm();
    fireEvent.click(screen.getByRole('button', { name: 'questions' }));
    fireEvent.click(screen.getByRole('button', { name: 'add question' }));
    fireEvent.change(screen.getByLabelText('question'), { target: { value: 'dietary needs?' } });
    const input = screen.getByLabelText('question');

    const event = pressEnter(input, input.closest('form')!);
    // Nested dialog form keeps its Enter-to-save: the guard must not block it.
    expect(event.defaultPrevented).toBe(false);

    // The dialog's own submit fired: it closed and the question was added.
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(screen.getByText('dietary needs?')).toBeInTheDocument();
    // The outer EventForm neither submitted nor created anything.
    expect(onSubmit).not.toHaveBeenCalled();
    expect(createEvent).not.toHaveBeenCalled();
  });

  it('enter with an empty label in the question dialog shows the dialog error, leaving the outer form alone', () => {
    const { onSubmit } = renderForm();
    fireEvent.click(screen.getByRole('button', { name: 'questions' }));
    fireEvent.click(screen.getByRole('button', { name: 'add question' }));
    const input = screen.getByLabelText('question');

    const event = pressEnter(input, input.closest('form')!);
    expect(event.defaultPrevented).toBe(false);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('question required');
    expect(onSubmit).not.toHaveBeenCalled();
    expect(createEvent).not.toHaveBeenCalled();
  });

  it('edit flow: enter in an input does not update, clicking save does', () => {
    const { form, onSubmit } = renderForm(makeEvent({ title: 'Beach cleanup' }));
    fireEvent.change(screen.getByLabelText('title'), { target: { value: 'Beach cleanup v2' } });

    pressEnter(screen.getByLabelText('title'), form);

    expect(onSubmit).not.toHaveBeenCalled();
    expect(updateEvent).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'save' }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(updateEvent).toHaveBeenCalledTimes(1);
    expect(updateEvent.mock.calls[0]![0]).toMatchObject({ title: 'Beach cleanup v2' });
    expect(createEvent).not.toHaveBeenCalled();
  });

  it('clicking the save button saves a draft', () => {
    renderForm();
    fireEvent.change(screen.getByLabelText('title'), { target: { value: 'beach day' } });
    fireEvent.click(screen.getByRole('switch'));

    fireEvent.click(screen.getByRole('button', { name: 'save' }));

    expect(createEvent).toHaveBeenCalledTimes(1);
    expect(createEvent.mock.calls[0]![0]).toMatchObject({ status: 'draft' });
  });

  it('clicking the publish button still submits', () => {
    const { onSubmit } = renderForm();
    fireEvent.change(screen.getByLabelText('title'), { target: { value: 'beach day' } });
    fireEvent.click(screen.getByRole('switch'));

    fireEvent.click(screen.getByRole('button', { name: 'publish' }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(createEvent).toHaveBeenCalledTimes(1);
  });
});
