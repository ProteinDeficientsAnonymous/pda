import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/auth/store';

import { DeleteAccountSection } from './DeleteAccountSection';

const deleteAccount = vi.fn<() => Promise<void>>();

function renderSection() {
  return render(
    <MemoryRouter initialEntries={['/settings']}>
      <Routes>
        <Route path="/settings" element={<DeleteAccountSection />} />
        <Route path="/" element={<div>home page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

async function openDialog() {
  await userEvent.click(screen.getByRole('button', { name: 'delete my account' }));
}

describe('DeleteAccountSection', () => {
  beforeEach(() => {
    deleteAccount.mockReset();
    useAuthStore.setState({ deleteAccount });
  });

  it('warns about whatsapp removal before opening the dialog', () => {
    renderSection();
    expect(screen.getByText(/removed from the pda whatsapp group/)).toBeInTheDocument();
  });

  it('keeps delete disabled until the confirm word is typed', async () => {
    renderSection();
    await openDialog();
    const confirmButton = screen.getByRole('button', { name: 'delete account' });
    expect(confirmButton).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/to confirm/), 'delete');
    expect(confirmButton).toBeEnabled();
  });

  it('deletes and navigates home', async () => {
    deleteAccount.mockResolvedValueOnce(undefined);
    renderSection();
    await openDialog();
    await userEvent.type(screen.getByLabelText(/to confirm/), 'delete');
    await userEvent.click(screen.getByRole('button', { name: 'delete account' }));
    await waitFor(() => {
      expect(screen.getByText('home page')).toBeInTheDocument();
    });
    expect(deleteAccount).toHaveBeenCalledOnce();
  });

  it('shows an error when deletion fails', async () => {
    deleteAccount.mockRejectedValueOnce(new Error('boom'));
    renderSection();
    await openDialog();
    await userEvent.type(screen.getByLabelText(/to confirm/), 'delete');
    await userEvent.click(screen.getByRole('button', { name: 'delete account' }));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
