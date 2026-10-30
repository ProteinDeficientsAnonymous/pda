import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { Permission } from '@/models/permissions';
import { setAuthed } from '@/test/auth';
import { makeUser } from '@/test/fixtures';

import AdminHubScreen from './AdminHubScreen';

function renderHub() {
  return render(
    <MemoryRouter>
      <AdminHubScreen />
    </MemoryRouter>,
  );
}

describe('AdminHubScreen', () => {
  it('shows the docs tile for a permitted user', () => {
    const user = makeUser({
      roles: [
        {
          id: 'r1',
          name: 'docs-admin',
          isDefault: true,
          permissions: [Permission.ManageDocuments],
        },
      ],
    });
    setAuthed(user, 'tok-abc');

    renderHub();

    expect(screen.getByText('docs')).toBeInTheDocument();
  });

  it('hides the docs tile for a user without the permission', () => {
    const user = makeUser({ roles: [] });
    setAuthed(user, 'tok-abc');

    renderHub();

    expect(screen.queryByText('docs')).not.toBeInTheDocument();
  });
});
