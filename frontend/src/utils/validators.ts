const displayNameRe = /^[\p{L}\p{M}' .-]+$/u;

export function displayName(value: string | null | undefined): string | null {
  if (!value || value.trim() === '') {
    return 'Required';
  }
  if (!displayNameRe.test(value.trim())) {
    return 'letters, spaces, hyphens, and apostrophes only';
  }
  if (value.trim().length > 64) {
    return 'Max 64 characters';
  }
  return null;
}

export function optionalDisplayName(value: string | null | undefined): string | null {
  if (!value || value.trim() === '') {
    return null;
  }
  if (!displayNameRe.test(value.trim())) {
    return 'letters, spaces, hyphens, and apostrophes only';
  }
  if (value.trim().length > 64) {
    return 'Max 64 characters';
  }
  return null;
}

const emailRe = /^[a-zA-Z0-9.!#$%&*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$/;

export function optionalEmail(value: string | null | undefined): string | null {
  if (!value || value.trim() === '') {
    return null;
  }
  if (!emailRe.test(value.trim())) {
    return 'enter a valid email address';
  }
  return null;
}

export function optionalUrl(
  value: string | null | undefined,
  options?: { httpsOnly?: boolean; requirePath?: boolean },
): string | null {
  if (!value || value.trim() === '') {
    return null;
  }
  const s = value.trim();
  const normalized = s.startsWith('http') ? s : `https://${s}`;
  try {
    const url = new globalThis.URL(normalized);
    if (!url.hostname) {
      return 'enter a valid URL';
    }
    if (options?.httpsOnly && url.protocol !== 'https:') {
      return 'URL must use https';
    }
    if (options?.requirePath && url.pathname.replaceAll('/', '').length === 0) {
      return 'link must point to a specific page, not just the domain';
    }
    return null;
  } catch {
    return 'enter a valid URL';
  }
}

export function password(value: string | null | undefined): string | null {
  if (!value || value.trim() === '') {
    return 'Required';
  }
  if (value.length < 12) {
    return 'at least 12 characters';
  }
  if (!/[A-Z]/.test(value)) {
    return 'include an uppercase letter';
  }
  if (!/[0-9]/.test(value)) {
    return 'include a number';
  }
  if (!/[^A-Za-z0-9]/.test(value)) {
    return 'include a special character';
  }
  return null;
}

const roleNameRe = /^[a-zA-Z0-9_-]+$/;

export function roleName(value: string | null | undefined): string | null {
  if (!value || value.trim() === '') {
    return 'Required';
  }
  if (!roleNameRe.test(value.trim())) {
    return 'Letters, numbers, underscores and hyphens only';
  }
  if (value.trim().length > 50) {
    return 'Max 50 characters';
  }
  return null;
}

export function required(value: string | null | undefined): string | null {
  if (!value || value.trim() === '') {
    return 'Required';
  }
  return null;
}

export function maxLength(max: number) {
  return (value: string | null | undefined): string | null => {
    if (value && value.trim().length > max) {
      return `Max ${String(max)} characters`;
    }
    return null;
  };
}

export function minLength(
  min: number,
  message?: string,
): (value: string | null | undefined) => string | null {
  return (value: string | null | undefined): string | null => {
    if (!value || value.trim() === '') {
      return null;
    }
    if (value.trim().length < min) {
      return message ?? `At least ${String(min)} characters required`;
    }
    return null;
  };
}
