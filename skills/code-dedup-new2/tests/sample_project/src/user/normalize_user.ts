export function normalizeUser(input: Record<string, unknown>) {
  const result: Record<string, unknown> = {};
  const name = String(input.name ?? "").trim();
  const email = String(input.email ?? "").trim().toLowerCase();
  const enabled = Boolean(input.enabled ?? true);
  result.name = name;
  result.email = email;
  result.enabled = enabled;
  result.type = "user";
  if (!result.name) {
    result.name = "unknown";
  }
  return result;
}

