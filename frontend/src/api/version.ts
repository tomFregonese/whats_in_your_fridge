const VERSION_RE = /^v?(\d+)\.(\d+)\.(\d+)/;

/** Strips any `-rcN` (or other) suffix and compares only the numeric
 * major.minor.patch triple. This project's own tag-format convention
 * (enforced by docker-build.yml's tag validation) guarantees `latest` is
 * always a clean `vX.Y.Z`, and `current` is either that or `vX.Y.Z-rcN` — a
 * small regex + numeric tuple compare is sufficient, no semver library
 * needed. Non-matching input (e.g. "dev" in local development) returns
 * false, so the banner never shows outside a real release build. */
export function isNewerVersion(current: string, latest: string): boolean {
  const currentMatch = VERSION_RE.exec(current);
  const latestMatch = VERSION_RE.exec(latest);
  if (!currentMatch || !latestMatch) {
    return false;
  }
  for (let i = 1; i <= 3; i++) {
    const c = Number(currentMatch[i]);
    const l = Number(latestMatch[i]);
    if (l !== c) return l > c;
  }
  return false;
}
