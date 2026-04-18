// Hand-written until `pnpm types:api` is run against a live backend. When the
// generated types come online, swap these for `components['schemas']['UserOut']`
// narrowings in api/auth.ts — this file should disappear.

export interface Role {
  id: string;
  name: string;
  isDefault: boolean;
  permissions: string[];
}

export interface User {
  id: string;
  phoneNumber: string;
  displayName: string;
  email: string;
  bio: string;
  isSuperuser: boolean;
  isStaff: boolean;
  needsOnboarding: boolean;
  showPhone: boolean;
  showEmail: boolean;
  weekStart: number;
  profilePhotoUrl: string;
  photoUpdatedAt: string | null;
  roles: Role[];
}
