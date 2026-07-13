import { api } from "./client";
import { Alert } from "../types";

export function getAlerts(limit?: number): Promise<Alert[]> {
  const query = limit ? `?limit=${limit}` : "";
  return api.get<{ alerts: Alert[] }>(`/api/alerts${query}`).then((res) => res.alerts);
}

export function getAlertHistory(): Promise<Alert[]> {
  return api.get<{ alerts: Alert[] }>(`/api/alerts/history`).then((res) => res.alerts);
}

export function markFalseAlarm(alertId: number): Promise<void> {
  return api.post(`/api/alerts/${alertId}/false_alarm`).then(() => undefined);
}
