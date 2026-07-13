import React, { useCallback, useEffect, useState } from "react";
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Alert as RNAlert } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { getPendingReportsForMe, validatePeerReport } from "../api/peerReports";
import { PeerReport } from "../types";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "PeerReportValidator">;

export default function PeerReportValidatorScreen({ route, navigation }: Props) {
  const { reportId } = route.params;
  const [report, setReport] = useState<PeerReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState(false);

  const load = useCallback(async () => {
    try {
      const pending = await getPendingReportsForMe();
      setReport(pending.find((r) => r.id === reportId) ?? null);
    } catch {
      // leave report null -- shows "not found" state below
    } finally {
      setLoading(false);
    }
  }, [reportId]);

  useEffect(() => {
    load();
  }, [load]);

  const onValidate = async (confirmed: boolean) => {
    setResolving(true);
    try {
      await validatePeerReport(reportId, confirmed);
      RNAlert.alert(
        confirmed ? "Confirmed" : "Dismissed",
        confirmed
          ? "The community has been notified."
          : "Marked as a false alarm -- no further action.",
        [{ text: "OK", onPress: () => navigation.goBack() }]
      );
    } catch (e) {
      RNAlert.alert("Failed", e instanceof Error ? e.message : "Could not resolve report.");
    } finally {
      setResolving(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Suspicious Activity Report</Text>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={styles.closeButton}>Close</Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <ActivityIndicator size="large" color="#fff" style={styles.loading} />
      ) : !report ? (
        <View style={styles.loading}>
          <Text style={styles.notFoundText}>
            This report is no longer pending (already resolved, or from a previous session).
          </Text>
        </View>
      ) : (
        <View style={styles.content}>
          <Text style={styles.reporterLabel}>Reported by</Text>
          <Text style={styles.reporterName}>{report.reporter_username}</Text>

          {report.message ? (
            <>
              <Text style={styles.sectionLabel}>Note</Text>
              <Text style={styles.messageText}>{report.message}</Text>
            </>
          ) : (
            <Text style={styles.messageText}>No additional details provided.</Text>
          )}

          <Text style={styles.sectionLabel}>Time</Text>
          <Text style={styles.messageText}>{report.timestamp}</Text>

          <Text style={styles.prompt}>Is this real suspicious activity on your camera?</Text>

          <View style={styles.decisionRow}>
            <TouchableOpacity style={styles.dismissButton} onPress={() => onValidate(false)} disabled={resolving}>
              {resolving ? <ActivityIndicator color="#fff" /> : <Text style={styles.dismissButtonText}>False Alarm</Text>}
            </TouchableOpacity>
            <TouchableOpacity style={styles.confirmButton} onPress={() => onValidate(true)} disabled={resolving}>
              {resolving ? <ActivityIndicator color="#fff" /> : <Text style={styles.confirmButtonText}>Confirm &amp; Notify Community</Text>}
            </TouchableOpacity>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 16, paddingTop: 50 },
  title: { color: "#fff", fontSize: 18, fontWeight: "700", flexShrink: 1 },
  closeButton: { color: "#60a5fa", fontSize: 16, fontWeight: "600" },
  loading: { flex: 1, justifyContent: "center", alignItems: "center", padding: 24 },
  notFoundText: { color: "#64748b", textAlign: "center" },
  content: { padding: 16 },
  reporterLabel: { color: "#64748b", fontSize: 12, textTransform: "uppercase", marginBottom: 4 },
  reporterName: { color: "#fff", fontSize: 20, fontWeight: "700", marginBottom: 20 },
  sectionLabel: { color: "#64748b", fontSize: 12, textTransform: "uppercase", marginBottom: 4, marginTop: 12 },
  messageText: { color: "#e2e8f0", fontSize: 14 },
  prompt: { color: "#fff", fontSize: 16, fontWeight: "600", marginTop: 28, marginBottom: 16 },
  decisionRow: { gap: 12 },
  dismissButton: { backgroundColor: "#334155", borderRadius: 10, paddingVertical: 16, alignItems: "center" },
  dismissButtonText: { color: "#e2e8f0", fontWeight: "700" },
  confirmButton: { backgroundColor: "#dc2626", borderRadius: 10, paddingVertical: 16, alignItems: "center" },
  confirmButtonText: { color: "#fff", fontWeight: "700" },
});
