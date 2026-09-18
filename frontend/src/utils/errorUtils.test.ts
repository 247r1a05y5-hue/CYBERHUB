import { describe, it, expect } from "vitest";
import { normalizeApiError, formatErrorMessage, safeRenderText } from "./errorUtils";

describe("errorUtils", () => {
  it("normalizes string errors", () => {
    const res = normalizeApiError("Network error occurred");
    expect(res.message).toBe("Network error occurred");
  });

  it("normalizes object errors with code and message", () => {
    const res = normalizeApiError({
      code: "REFERENCE_IMAGE_NOT_EXTERNALLY_REACHABLE",
      message: "SearchAPI requires a public URL.",
    });
    expect(res.code).toBe("REFERENCE_IMAGE_NOT_EXTERNALLY_REACHABLE");
    expect(res.message).toBe("SearchAPI requires a public URL.");
  });

  it("normalizes Axios response data error structures", () => {
    const res = normalizeApiError({
      response: {
        status: 400,
        data: {
          detail: {
            code: "PROVIDER_FAILURE",
            message: "Google Lens rate limit exceeded.",
          },
        },
      },
    });
    expect(res.code).toBe("PROVIDER_FAILURE");
    expect(res.message).toBe("Google Lens rate limit exceeded.");
  });

  it("normalizes FastAPI validation error array", () => {
    const res = normalizeApiError({
      response: {
        status: 422,
        data: {
          detail: [
            {
              loc: ["body", "file"],
              msg: "Field required",
              type: "value_error.missing",
            },
          ],
        },
      },
    });
    expect(res.message).toBe("Field required");
  });

  it("formats error messages safely", () => {
    const msg = formatErrorMessage({
      code: "SEARCH_FAILED",
      message: "Upstream provider timed out",
    });
    expect(msg).toBe("[SEARCH_FAILED] Upstream provider timed out");
  });

  it("safeRenderText converts raw error objects into string without throwing", () => {
    const rawObj = { code: "ERR_123", message: "Critical failure" };
    expect(safeRenderText(rawObj)).toBe("[ERR_123] Critical failure");
    expect(safeRenderText("Plain string")).toBe("Plain string");
    expect(safeRenderText(null)).toBe("");
  });
});
