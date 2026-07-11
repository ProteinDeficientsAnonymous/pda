import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { emptyEventFormValues, type EventFormValues } from '@/api/eventWrites';

import { EventFormType } from './EventFormType';

function values(overrides: Partial<EventFormValues> = {}): EventFormValues {
  return { ...emptyEventFormValues(), ...overrides };
}

describe('EventFormType', () => {
  it('renders nothing without tag-official permission', () => {
    const { container } = render(
      <EventFormType values={values()} onChange={vi.fn()} canTagOfficial={false} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('turning the toggle on sets official type and forces public visibility', async () => {
    const onChange = vi.fn();
    render(
      <EventFormType
        values={values({ visibility: 'members_only' })}
        onChange={onChange}
        canTagOfficial
      />,
    );
    await userEvent.click(screen.getByRole('switch'));
    expect(onChange).toHaveBeenCalledWith({ eventType: 'official', visibility: 'public' });
  });

  it('turning the toggle off reverts to community without touching visibility', async () => {
    const onChange = vi.fn();
    render(
      <EventFormType
        values={values({ eventType: 'official' })}
        onChange={onChange}
        canTagOfficial
      />,
    );
    await userEvent.click(screen.getByRole('switch'));
    expect(onChange).toHaveBeenCalledWith({ eventType: 'community' });
  });
});
