import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { emptyEventFormValues, type EventFormValues } from '@/api/eventWrites';

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

  it('official toggle sets official type and forces public visibility', async () => {
    const onChange = vi.fn();
    render(
      <EventFormType
        values={values({ visibility: 'members_only' })}
        onChange={onChange}
        canTagOfficial
        canTagClub={false}
      />,
    );
    await userEvent.click(screen.getByRole('switch'));
    expect(onChange).toHaveBeenCalledWith({ eventType: 'official', visibility: 'public' });
  });

  it('club toggle sets club type and forces public visibility', async () => {
    const onChange = vi.fn();
    render(
      <EventFormType
        values={values({ visibility: 'members_only' })}
        onChange={onChange}
        canTagOfficial={false}
        canTagClub
      />,
    );
    await userEvent.click(screen.getByRole('switch'));
    expect(onChange).toHaveBeenCalledWith({ eventType: 'club', visibility: 'public' });
  });

  it('turning a type off reverts to community without forcing visibility', async () => {
    const onChange = vi.fn();
    render(
      <EventFormType
        values={values({ eventType: 'official' })}
        onChange={onChange}
        canTagOfficial
        canTagClub={false}
      />,
    );
    await userEvent.click(screen.getByRole('switch'));
    expect(onChange).toHaveBeenCalledWith({ eventType: 'community' });
  });

  it('with both permissions, the club toggle is off while official is selected', () => {
    render(
      <EventFormType
        values={values({ eventType: 'official' })}
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
});
