import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { getHealth } from "../api/health";
import { getLatestReleaseTag } from "../api/releaseCheck";
import { isNewerVersion } from "../api/version";

/** Checks once per mount whether a newer final release exists on GitHub than
 * the one this backend was built from, and shows a passive, dismiss-free
 * notice pointing at the Releases page if so. No auto-update — closing and
 * replacing the app is left entirely to the launcher scripts (see
 * release/README.txt). Silent whenever there's nothing to report:
 * same-or-newer version, a local/dev build ("dev"), or the check didn't
 * resolve (see releaseCheck.ts for why that's never an error). */
export function UpdateAvailableBanner() {
  const [latestTag, setLatestTag] = useState<string | null>(null);
  const location = useLocation();

  useEffect(() => {
    let cancelled = false;
    Promise.all([getHealth(), getLatestReleaseTag()])
      .then(([health, latest]) => {
        if (!cancelled && latest && isNewerVersion(health.version, latest)) {
          setLatestTag(latest);
        }
      })
      .catch(() => {
        // getHealth() failing is already surfaced elsewhere in the app;
        // this banner just has nothing to report either way.
      });
    return () => {
      cancelled = true;
    };
  }, [location.pathname]);

  if (latestTag === null) {
    return null;
  }

  return (
    <a
      href="https://github.com/tomFregonese/whats_in_your_fridge/releases"
      target="_blank"
      rel="noreferrer"
      className="update-available-banner"
    >
      <span className="update-available-banner-icon">⬆️</span>
      <span>
        A new version (<strong>{latestTag}</strong>) is available — close the app, download it,
        and relaunch.
      </span>
    </a>
  );
}
