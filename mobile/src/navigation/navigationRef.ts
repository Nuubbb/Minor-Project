import { createNavigationContainerRef } from "@react-navigation/native";
import type { RootStackParamList } from "./types";

export const navigationRef = createNavigationContainerRef<RootStackParamList>();

export function navigateToAlertValidator(alertId: number) {
  if (navigationRef.isReady()) {
    navigationRef.navigate("AlertValidator", { alertId });
  }
}

export function navigateToPeerReportValidator(reportId: number) {
  if (navigationRef.isReady()) {
    navigationRef.navigate("PeerReportValidator", { reportId });
  }
}
