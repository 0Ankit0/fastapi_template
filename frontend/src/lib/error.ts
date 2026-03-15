/** Safely extract a human-readable message from an Axios/fetch error.
 *  Handles FastAPI's string detail, validation-error arrays, and plain Errors. */
export function extractErrorMsg(e: unknown, fallback = 'Something went wrong.'): string {
  const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (detail === undefined || detail === null) {
    // Fallback to Error.message
    if (e instanceof Error) return e.message;
    return fallback;
  }
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    // FastAPI validation errors: [{msg, loc, type, input}, ...]
    return detail
      .map((d) =>
        typeof d === 'object' && d !== null
          ? (d as { msg?: string }).msg ?? JSON.stringify(d)
          : String(d),
      )
      .join('; ');
  }
  if (typeof detail === 'object') {
    return (detail as { message?: string; msg?: string }).message
      ?? (detail as { message?: string; msg?: string }).msg
      ?? JSON.stringify(detail);
  }
  return String(detail);
}
