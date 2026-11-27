import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { MemberBlast } from '@/api/memberBlast';

import { MemberBlastHistory } from './MemberBlastHistory';

const blast = {
  id: '1',
  subject: 'hello all',
  status: 'sent',
  created_at: '2026-11-27T12:00:00Z',
} as MemberBlast;

describe('MemberBlastHistory', () => {
  it('renders subject, status and lowercase date', () => {
    render(<MemberBlastHistory blasts={[blast]} />);
    expect(screen.getByText('hello all')).toBeTruthy();
    expect(screen.getByText('sent · nov 27, 2026')).toBeTruthy();
  });

  it('renders nothing when empty', () => {
    const { container } = render(<MemberBlastHistory blasts={[]} />);
    expect(container.innerHTML).toBe('');
  });
});
