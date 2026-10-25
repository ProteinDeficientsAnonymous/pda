import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { makeUser } from '@/test/fixtures';

import { EmailPreferences } from './EmailPreferences';

function renderPrefs(overrides: Partial<ReturnType<typeof makeUser>> = {}) {
  const onChange = vi.fn();
  const user = { ...makeUser(), ...overrides };
  render(<EmailPreferences user={user} onChange={onChange} />);
  return { onChange };
}

describe('EmailPreferences', () => {
  it('shows the whatsapp reminder toggle on when the user has not opted out', () => {
    renderPrefs({ whatsappReminderOptOut: false });
    expect(screen.getByRole('switch', { name: /reminders to join the whatsapp/i })).toHaveAttribute(
      'aria-checked',
      'true',
    );
  });

  it('shows the whatsapp reminder toggle off when the user has opted out', () => {
    renderPrefs({ whatsappReminderOptOut: true });
    expect(screen.getByRole('switch', { name: /reminders to join the whatsapp/i })).toHaveAttribute(
      'aria-checked',
      'false',
    );
  });

  it('opts out when the whatsapp reminder toggle is switched off', async () => {
    const { onChange } = renderPrefs({ whatsappReminderOptOut: false });
    await userEvent.click(screen.getByRole('switch', { name: /reminders to join the whatsapp/i }));
    expect(onChange).toHaveBeenCalledWith({ whatsappReminderOptOut: true });
  });

  it('opts back in when the whatsapp reminder toggle is switched on', async () => {
    const { onChange } = renderPrefs({ whatsappReminderOptOut: true });
    await userEvent.click(screen.getByRole('switch', { name: /reminders to join the whatsapp/i }));
    expect(onChange).toHaveBeenCalledWith({ whatsappReminderOptOut: false });
  });

  it('hides the in-person reminder toggle from full members', () => {
    renderPrefs({ isMember: true });
    expect(screen.queryByRole('switch', { name: /come to an event in person/i })).toBeNull();
  });

  it('lets a tentative member opt out of in-person reminders', async () => {
    const { onChange } = renderPrefs({ isMember: false, attendanceNudgeOptOut: false });
    const toggle = screen.getByRole('switch', { name: /come to an event in person/i });
    expect(toggle).toHaveAttribute('aria-checked', 'true');
    await userEvent.click(toggle);
    expect(onChange).toHaveBeenCalledWith({ attendanceNudgeOptOut: true });
  });

  it('shows the host updates toggle off when opted out', () => {
    renderPrefs({ hostDigestOptOut: true });
    expect(screen.getByRole('switch', { name: /updates about events i host/i })).toHaveAttribute(
      'aria-checked',
      'false',
    );
  });

  it('opts out when the host updates toggle is switched off', async () => {
    const { onChange } = renderPrefs({ hostDigestOptOut: false });
    await userEvent.click(screen.getByRole('switch', { name: /updates about events i host/i }));
    expect(onChange).toHaveBeenCalledWith({ hostDigestOptOut: true });
  });

  it('leaves the weekly digest toggle working independently', async () => {
    const { onChange } = renderPrefs({ weeklyDigestOptOut: false });
    await userEvent.click(screen.getByRole('switch', { name: /weekly digest/i }));
    expect(onChange).toHaveBeenCalledWith({ weeklyDigestOptOut: true });
  });

  it('leaves veganniversaries out of the monthly digest label for tentative members', () => {
    renderPrefs({ isMember: false });
    expect(screen.getByRole('switch', { name: 'monthly digest of events' })).toBeInTheDocument();
  });

  it('opts out of the monthly digest separately from the weekly one', async () => {
    const { onChange } = renderPrefs({ monthlyDigestOptOut: false });
    await userEvent.click(screen.getByRole('switch', { name: /monthly digest/i }));
    expect(onChange).toHaveBeenCalledWith({ monthlyDigestOptOut: true });
  });
});
