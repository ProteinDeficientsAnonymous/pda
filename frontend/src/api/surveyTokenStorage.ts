const STORAGE_PREFIX = 'pda-survey-token:';

function key(slug: string): string {
  return `${STORAGE_PREFIX}${slug}`;
}

export function getStoredSurveyToken(slug: string): string | null {
  try {
    return localStorage.getItem(key(slug));
  } catch {
    return null;
  }
}

export function setStoredSurveyToken(slug: string, token: string): void {
  try {
    localStorage.setItem(key(slug), token);
  } catch {
    // storage unavailable (private mode / blocked) — the survey still submits, just without dedupe
  }
}
