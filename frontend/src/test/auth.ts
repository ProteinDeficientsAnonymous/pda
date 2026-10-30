import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';

import { makeUser } from './fixtures';

export function setAuthed(user: User = makeUser(), accessToken = 'tok') {
  useAuthStore.setState({ status: 'authed', user, accessToken });
}

export function setUnauthed() {
  useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
}
