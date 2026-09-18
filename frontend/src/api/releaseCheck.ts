const RELEASES_URL =
  "https://api.github.com/repos/tomFregonese/whats_in_your_fridge/releases/latest";

/** Calls GitHub's public REST API directly (bypassing `api/client.ts`, which
 * only targets this app's own same-origin backend and assumes its
 * `{detail}`-JSON error shape — neither holds here). This endpoint sends
 * permissive CORS headers for public, unauthenticated GET requests, so no
 * backend proxy is needed. Returns null whenever there's nothing to report —
 * offline, rate-limited (60 req/hour/IP unauthenticated), or no release
 * exists yet (404 until the first final tag is promoted) — never throws, so
 * a flaky/absent check can't block the rest of the UI. */
export async function getLatestReleaseTag(): Promise<string | null> {
  try {
    const response = await fetch(RELEASES_URL);
    if (!response.ok) {
      return null;
    }
    const data = (await response.json()) as { tag_name?: string };
    return data.tag_name ?? null;
  } catch {
    return null;
  }
}
