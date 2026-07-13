import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from "react";
import { getAlerts } from "../api/alerts";

interface AlertBadgeContextValue {
  unseenCount: number;
  markSeen: () => void;
}

const AlertBadgeContext = createContext<AlertBadgeContextValue | undefined>(undefined);

const POLL_MS = 3000;

/**
 * In-app "notification" indicator: polls for new alerts regardless of which
 * tab is active and tracks how many haven't been seen yet, shown as a badge
 * on the Dashboard tab icon. (Real OS push notifications via expo-notifications
 * don't work in Expo Go on Android as of SDK 53 -- would need a custom dev
 * build -- so this is the in-app equivalent.)
 */
export function AlertBadgeProvider({ children }: { children: React.ReactNode }) {
  const [unseenCount, setUnseenCount] = useState(0);
  const lastSeenId = useRef<number | null>(null);
  const initialized = useRef(false);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        const alerts = await getAlerts(20); // newest first
        if (cancelled || alerts.length === 0) return;

        if (!initialized.current) {
          // Baseline only -- don't badge for alerts that predate this session.
          lastSeenId.current = alerts[0].id;
          initialized.current = true;
          return;
        }

        const newOnes = alerts.filter(
          (a) => lastSeenId.current !== null && a.id > lastSeenId.current && !a.is_false_alarm
        );
        lastSeenId.current = Math.max(lastSeenId.current!, ...alerts.map((a) => a.id));
        if (newOnes.length > 0) {
          setUnseenCount((c) => c + newOnes.length);
        }
      } catch {
        // network hiccup -- just retry on the next tick
      }
    };

    poll();
    const interval = setInterval(poll, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const markSeen = useCallback(() => setUnseenCount(0), []);

  return <AlertBadgeContext.Provider value={{ unseenCount, markSeen }}>{children}</AlertBadgeContext.Provider>;
}

export function useAlertBadge(): AlertBadgeContextValue {
  const ctx = useContext(AlertBadgeContext);
  if (!ctx) throw new Error("useAlertBadge must be used within AlertBadgeProvider");
  return ctx;
}
