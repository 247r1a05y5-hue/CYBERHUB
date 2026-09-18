export interface NormalizedError {
  code?: string;
  message: string;
  details?: Record<string, unknown> | Array<unknown>;
}

/**
 * Normalizes any error object, string, Axios response, or FastAPI detail structure
 * into a uniform NormalizedError object { code, message, details }.
 */
export function normalizeApiError(
  error: unknown,
  fallbackMessage = "An unexpected error occurred."
): NormalizedError {
  if (!error) {
    return { message: fallbackMessage };
  }

  if (typeof error === "string") {
    return { message: error };
  }

  if (typeof error === "object") {
    const errObj = error as Record<string, any>;

    // 1. Axios / Fetch HTTP Response object
    if (errObj.response && errObj.response.data) {
      const data = errObj.response.data;

      // FastAPI validation error array: detail = [{ loc: [...], msg: "..." }]
      if (Array.isArray(data.detail)) {
        const first = data.detail[0];
        const msg =
          typeof first === "string"
            ? first
            : first?.msg || first?.message || JSON.stringify(first);
        return {
          code: data.code || errObj.response.status?.toString() || "VALIDATION_ERROR",
          message: msg || fallbackMessage,
          details: data.detail,
        };
      }

      // detail object: detail = { code: "...", message: "..." }
      if (data.detail && typeof data.detail === "object") {
        return {
          code: data.detail.code || data.code || errObj.response.status?.toString(),
          message:
            data.detail.message ||
            data.detail.msg ||
            data.detail.error ||
            JSON.stringify(data.detail),
          details: data.detail,
        };
      }

      // detail string
      if (typeof data.detail === "string" && data.detail.trim().length > 0) {
        return {
          code: data.code || data.error_code || errObj.response.status?.toString(),
          message: data.detail,
        };
      }

      // error object inside response data: data.error = { code: "...", message: "..." }
      if (data.error && typeof data.error === "object") {
        return {
          code: data.error.code || data.code,
          message:
            data.error.message || data.error.msg || JSON.stringify(data.error),
          details: data.error,
        };
      }

      // error string inside response data
      if (typeof data.error === "string" && data.error.trim().length > 0) {
        return {
          code: data.code,
          message: data.error,
        };
      }

      // message inside response data: data.message
      if (typeof data.message === "string" && data.message.trim().length > 0) {
        return {
          code: data.code,
          message: data.message,
        };
      }

      if (typeof data.message === "object" && data.message) {
        return {
          code: data.message.code || data.code,
          message:
            data.message.message || data.message.msg || JSON.stringify(data.message),
        };
      }
    }

    // 2. Direct object with { code, message } or { code, detail } or { message }
    if (typeof errObj.message === "string" && errObj.message.trim().length > 0) {
      return {
        code: typeof errObj.code === "string" ? errObj.code : undefined,
        message: errObj.message,
      };
    }

    if (typeof errObj.detail === "string" && errObj.detail.trim().length > 0) {
      return {
        code: typeof errObj.code === "string" ? errObj.code : undefined,
        message: errObj.detail,
      };
    }

    if (typeof errObj.detail === "object" && errObj.detail) {
      return normalizeApiError(errObj.detail, fallbackMessage);
    }

    if (typeof errObj.error === "string" && errObj.error.trim().length > 0) {
      return {
        code: typeof errObj.code === "string" ? errObj.code : undefined,
        message: errObj.error,
      };
    }

    if (typeof errObj.error === "object" && errObj.error) {
      return normalizeApiError(errObj.error, fallbackMessage);
    }

    // Standard JavaScript Error object
    if (error instanceof Error && error.message) {
      return { message: error.message };
    }
  }

  return { message: String(error) || fallbackMessage };
}

/**
 * Returns a human-readable string representation of an error, preserving code if present.
 */
export function formatErrorMessage(
  error: unknown,
  fallbackMessage = "An unexpected error occurred."
): string {
  const norm = normalizeApiError(error, fallbackMessage);
  if (norm.code) {
    return `[${norm.code}] ${norm.message}`;
  }
  return norm.message;
}

/**
 * Ensures any React child variable can be safely interpolated in JSX without throwing
 * "Objects are not valid as a React child".
 */
export function safeRenderText(value: unknown, fallback = ""): string {
  if (value === null || value === undefined) return fallback;
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (typeof value === "object") {
    const valObj = value as Record<string, any>;
    if (valObj.code && typeof valObj.message === "string") {
      return `[${valObj.code}] ${valObj.message}`;
    }
    if (typeof valObj.message === "string") return valObj.message;
    if (typeof valObj.msg === "string") return valObj.msg;
    if (typeof valObj.detail === "string") return valObj.detail;
    if (typeof valObj.error === "string") return valObj.error;
    try {
      return JSON.stringify(value);
    } catch {
      return fallback;
    }
  }
  return String(value);
}
