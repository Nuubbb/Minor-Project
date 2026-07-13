import { useEffect, useRef } from "react";
import { Platform } from "react-native";
import * as Notifications from "expo-notifications";
import { getAlerts } from "../api/alerts";
import { navigateToAlertValidator } from "../navigation/navigationRef";

const POLL_MS = 3000;

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

async function ensurePermissions() {
  const { status } = await Notifications.getPermissionsAsync();
  if (status !== "granted") {
    await Notifications.requestPermissionsAsync();
  }
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("alerts", {
      name: "Security alerts",
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
    });
  }
}

/**
 * Polls for new alerts and fires a real device notification for each one
 * that wasn't seen before, regardless of which tab is active. Requires a
 * custom dev-client build -- expo-notifications does not work in Expo Go on
 * Android as of SDK 53. The first poll after mount only establishes a
 * baseline; it doesn't notify for alerts that already existed before this
 * hook started running.
 */
export function useAlertNotifications() {
  const lastSeenId = useRef<number | null>(null);
  const initialized = useRef(false);

  useEffect(() => {
    let cancelled = false;
    ensurePermissions();

    // Tapping a notification (foreground/background) navigates to the validator.
    const subscription = Notifications.addNotificationResponseReceivedListener((response) => {
      const alertId = response.notification.request.content.data?.alertId;
      if (typeof alertId === "number") navigateToAlertValidator(alertId);
    });

    // Cold start (app was fully closed, user tapped the notification to open it).
    Notifications.getLastNotificationResponseAsync().then((response) => {
      const alertId = response?.notification.request.content.data?.alertId;
      if (typeof alertId === "number") navigateToAlertValidator(alertId);
    });

    const poll = async () => {
      try {
        const alerts = await getAlerts(20); // newest first
        if (cancelled || alerts.length === 0) return;

        if (!initialized.current) {
          // Baseline only -- don't notify for alerts that predate this session.
          lastSeenId.current = alerts[0].id;
          initialized.current = true;
          return;
        }

        const newOnes = alerts.filter(
          (a) => lastSeenId.current !== null && a.id > lastSeenId.current && !a.is_false_alarm
        );
        lastSeenId.current = Math.max(lastSeenId.current!, ...alerts.map((a) => a.id));
        if (newOnes.length > 0) {
          for (const a of newOnes.reverse()) {
            await Notifications.scheduleNotificationAsync({
              content: {
                title: `${a.alert_type.replace(/-/g, " ")} detected`,
                body: `Tap to take a look · ${(a.confidence * 100).toFixed(0)}% confidence`,
                data: { alertId: a.id },
              },
              trigger: null,
            });
          }
        }
      } catch (e) {
        console.error("[notifications] poll/schedule error:", e);
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
