import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { Dialog } from './Dialog';

describe('Dialog', () => {
  it('renders into document.body instead of the parent node', () => {
    const { container } = render(
      <div data-testid="parent">
        <Dialog open onClose={() => {}} title="ported">
          <p>body</p>
        </Dialog>
      </div>,
    );

    expect(container.querySelector('[role="dialog"]')).toBeNull();
    expect(document.body.querySelector('[role="dialog"]')).toBeTruthy();
  });

  it('shows a visible close button that calls onClose', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <Dialog open onClose={onClose} title="sample">
        <p>body</p>
      </Dialog>,
    );
    await user.click(screen.getByRole('button', { name: /^close$/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('should allow the narrow panel body to scroll when content exceeds max height', () => {
    render(
      <Dialog open onClose={() => {}} title="tall">
        <p>{'line\n'.repeat(80)}</p>
      </Dialog>,
    );
    const panel = document.body.querySelector('[role="dialog"] > div.bg-surface');
    expect(panel?.className).toMatch(/overflow-y-auto/);
    expect(panel?.className).not.toMatch(/overflow-hidden/);
  });
});
