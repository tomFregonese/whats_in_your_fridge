import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { ModelStatusBanner } from "./ModelStatusBanner";

/** Persistent header + nav wrapping every screen behind `AppGate` (Home,
 * Settings, and whatever gets added in later milestones). Onboarding and
 * Unlock stay chrome-free — they're focused, one-thing-at-a-time flows. */
export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <span className="app-logo">🧊 What's in your fridge?</span>
          <nav className="app-nav">
            <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
              Home
            </NavLink>
            <NavLink to="/history" className={({ isActive }) => (isActive ? "active" : "")}>
              History
            </NavLink>
            <NavLink to="/settings" className={({ isActive }) => (isActive ? "active" : "")}>
              Settings
            </NavLink>
          </nav>
        </div>
      </header>
      <ModelStatusBanner />
      <main className="app-content">{children}</main>
    </div>
  );
}
