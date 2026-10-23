import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { emptyEventFormValues, type EventFormValues } from '@/api/eventWrites';
import { EventType, EventVisibility } from '@/models/event';

import { EventFormType } from './EventFormType';

function values(overrides: Partial<EventFormValues> = {}): EventFormValues {
  return { ...emptyEventFormValues(), ...overrides };
}

describe('EventFormType', () => {
  it('renders nothing without either tag permission', () => {
    const { container } = render(
      <EventFormType
        values={values()}
        onChange={vi.fn()}
        canTagOfficial={false}
        canTagClub={false}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('shows only the official toggle when only official is permitted', () => {
    render(
      <EventFormType values={values()} onChange={vi.fn()} canTagOfficial canTagClub={false} />,
    );
    expect(screen.getByText('make it an official pda event')).toBeInTheDocument();
    expect(screen.queryByText('make it a pda club event')).not.toBeInTheDocument();
  });

  it('official toggle sets official type, forces public visibility, and turns off +1s', async () => {
    const onChange = vi.fn();
    render(
      <EventFormType
        values={values({ visibility: EventVisibility.MembersOnly })}
        onChange={onChange}
        canTagOfficial
        canTagClub={false}
      />,
    );
    await userEvent.click(screen.getByRole('switch'));
    expect(onChange).toHaveBeenCalledWith({
      eventType: EventType.Official,
      visibility: EventVisibility.Public,
      allowPlusOnes: false,
      cashappLink: '$pdanyc',
    });
  });

  it('club toggle sets club type, forces public visibility, and turns off +1s', async () => {
    const onChange = vi.fn();
    render(
      <EventFormType
        values={values({ visibility: EventVisibility.MembersOnly })}
        onChange={onChange}
        canTagOfficial={false}
        canTagClub
      />,
    );
    await userEvent.click(screen.getByRole('switch'));
    expect(onChange).toHaveBeenCalledWith({
      eventType: EventType.Club,
      visibility: EventVisibility.Public,
      allowPlusOnes: false,
    });
  });

  it('official toggle does not overwrite existing cashapp link', async () => {
    const onChange = vi.fn();
    render(
      <EventFormType
        values={values({ visibility: EventVisibility.MembersOnly, cashappLink: '@existinghandle' })}
        onChange={onChange}
        canTagOfficial
        canTagClub={false}
      />,
    );
    await userEvent.click(screen.getByRole('switch'));
    expect(onChange).toHaveBeenCalledWith({
      eventType: EventType.Official,
      visibility: EventVisibility.Public,
      allowPlusOnes: false,
    });
  });

  it('turning a type off reverts to community without forcing visibility or +1s', async () => {
    const onChange = vi.fn();
    render(
      <EventFormType
        values={values({ eventType: EventType.Official })}
        onChange={onChange}
        canTagOfficial
        canTagClub={false}
      />,
    );
    await userEvent.click(screen.getByRole('switch'));
    expect(onChange).toHaveBeenCalledWith({ eventType: EventType.Community });
  });

  it('with both permissions, the club toggle is off while official is selected', () => {
    render(
      <EventFormType
        values={values({ eventType: EventType.Official })}
        onChange={vi.fn()}
        canTagOfficial
        canTagClub
      />,
    );
    const switches = screen.getAllByRole('switch');
    expect(switches).toHaveLength(2);
    // official checked, club unchecked — single-value type is mutually exclusive
    expect(switches[0]).toHaveAttribute('aria-checked', 'true');
    expect(switches[1]).toHaveAttribute('aria-checked', 'false');
  });

  it('shows the walk toggle, on by default, for a new official event', () => {
    render(
      <EventFormType
        values={values({ eventType: EventType.Official })}
        onChange={vi.fn()}
        canTagOfficial
        canTagClub={false}
        showWalkToggle
      />,
    );
    expect(screen.getByRole('switch', { name: "it's a walk" })).toBeChecked();
  });

  it('turning the walk toggle off patches isWalk', async () => {
    const onChange = vi.fn();
    render(
      <EventFormType
        values={values({ eventType: EventType.Official })}
        onChange={onChange}
        canTagOfficial
        canTagClub={false}
        showWalkToggle
      />,
    );
    await userEvent.click(screen.getByRole('switch', { name: "it's a walk" }));
    expect(onChange).toHaveBeenCalledWith({ isWalk: false });
  });

  it('hides the walk toggle unless the event is official', () => {
    render(
      <EventFormType
        values={values()}
        onChange={vi.fn()}
        canTagOfficial
        canTagClub={false}
        showWalkToggle
      />,
    );
    expect(screen.queryByRole('switch', { name: "it's a walk" })).not.toBeInTheDocument();
  });
});
