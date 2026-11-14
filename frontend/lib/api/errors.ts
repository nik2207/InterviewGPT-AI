export function getApiErrorMessage(error: unknown): string {
  if (
    typeof error === "object" &&
    error !== null &&
    "response" in error
  ) {
    const response = (error as { response?: { data?: { detail?: unknown } } })
      .response;
    const detail = response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (
            typeof item === "object" &&
            item !== null &&
            "msg" in item &&
            typeof (item as { msg?: string }).msg === "string"
          ) {
            const loc = (item as { loc?: unknown[] }).loc;
            const field =
              Array.isArray(loc) && loc.length > 0
                ? String(loc[loc.length - 1])
                : "field";
            return `${field}: ${(item as { msg: string }).msg}`;
          }
          return null;
        })
        .filter(Boolean);
      if (messages.length > 0) {
        return messages.join(" ");
      }
    }
  }
  return "Something went wrong. Please try again.";
}
