import { useEffect, useRef } from "react";
import * as Notifications from "expo-notifications";
import { getPendingReportsForMe } from "../api/peerReports";
import { navigateToPeerReportValidator } from "../navigation/navigationRef";

const POLL_MS = 3000;

/**
 * Polls for pending peer reports where the logged-in user is the house
 * owner, and fires a real device notification for each new one -- same
 * pattern as useAlertNotifications, but for human-reported suspicious
 * activity rather than model-detected alerts. Permissions/channel setup are
 * shared/idempotent with useAlertNotifications (both call
 * getPermissionsAsync/requestPermissionsAsync, which is safe to do twice).
 */
export function usePeerReportNotifications() {
  const lastSeenId = useRef<number | null>(null);
  const initialized = useRef(false);

  useEffect(() => {
    let cancelled = false;

    const subscription = Notifications.addNotificationResponseReceivedListener((response) => {
      const reportId = response.notification.request.content.data?.peerReportId;
      if (typeof reportId === "number") navigateToPeerReportValidator(reportId);
    });

    Notifications.getLastNotificationResponseAsync().then((response) => {
      const reportId = response?.notification.request.content.data?.peerReportId;
      if (typeof reportId === "number") navigateToPeerReportValidator(reportId);
    });

    const poll = async () => {
      try {
        const reports = await getPendingReportsForMe(); // newest first
        if (cancelled || reports.length === 0) return;

        if (!initialized.current) {
          lastSeenId.current = reports[0].id;
          initialized.current = true;
          return;
        }

        const newOnes = reports.filter((r) => lastSeenId.current !== null && r.id > lastSeenId.current);
        lastSeenId.current = Math.max(lastSeenId.current!, ...reports.map((r) => r.id));
        if (newOnes.length > 0) {
          for (const r of newOnes.reverse()) {
            await Notifications.scheduleNotificationAsync({
              content: {
                title: "Suspicious activity reported on your camera",
                body: `${r.reporter_username} flagged something -- tap to review`,
                data: { peerReportId: r.id },
              },
              trigger: null,
            });
          }
        }
      } catch (e) {
        console.error("[peer-report notifications] poll/schedule error:", e);
      }
    };

    poll();
    const interval = setInterval(poll, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
      subscription.remove();
    };
  }, []);
}
