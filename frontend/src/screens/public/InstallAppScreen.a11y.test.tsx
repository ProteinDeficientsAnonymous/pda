import { describe, expect, it } from 'vitest';
import { axe } from 'vitest-axe';

import { renderWithProviders } from '@/test/render';

import InstallAppScreen from './InstallAppScreen';

describe('InstallAppScreen accessibility', () => {
  it('has no axe violations', async () => {
    const { container } = renderWithProviders(<InstallAppScreen />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
