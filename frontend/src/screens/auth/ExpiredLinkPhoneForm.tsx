import type { SyntheticEvent } from 'react';
import { useState } from 'react';
import { isValidPhoneNumber } from 'react-phone-number-input';
import { useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/Button';
import { PhoneField } from '@/components/ui/PhoneField';

export function ExpiredLinkPhoneForm() {
  const navigate = useNavigate();
  const [phone, setPhone] = useState('');
  const [error, setError] = useState<string | null>(null);

  function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    if (!phone || !isValidPhoneNumber(phone)) {
      setError('enter a valid phone number');
      return;
    }
    void navigate('/login', { replace: true, state: { phone } });
  }

  return (
    <form onSubmit={onSubmit} className="mt-4 flex flex-col gap-4">
      <PhoneField
        label="phone number"
        value={phone}
        onChange={setPhone}
        error={error ?? undefined}
        name="username"
        autoComplete="username"
      />
      <Button type="submit" fullWidth>
        continue
      </Button>
    </form>
  );
}
