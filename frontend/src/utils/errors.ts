// Re-exports for backwards compatibility — call sites that previously
// imported from `@/utils/errors` continue to work, but they now get the
// code-aware extractor from `@/api/apiErrors` (which understands both the
// legacy `{detail: "..."}` string shape and the new
// `{detail: [{code, field, params?}]}` structured shape).

export { extractApiErrorOr as extractApiError } from '@/api/apiErrors';
