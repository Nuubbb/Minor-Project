import React, { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  Image,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert as RNAlert,
} from "react-native";
import { WebView } from "react-native-webview";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useAuth } from "../context/AuthContext";
import { authenticatedFileUrl } from "../api/client";
import { getMessagePackets, sendMessagePacket } from "../api/messagePackets";
import { markFalseAlarm } from "../api/alerts";
import { buildMapHtml } from "../maps/mapHtml";
import { MessagePacket } from "../types";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "AlertValidator">;

type Decision = "pending" | "not_a_threat" | "confirmed_threat";

export default function AlertValidatorScreen({ route, navigation }: Props) {
  const { alertId } = route.params;
  const { user } = useAuth();
  const [packet, setPacket] = useState<MessagePacket | null>(null);
  const [loading, setLoading] = useState(true);
  const [decision, setDecision] = useState<Decision>("pending");
  const [marking, setMarking] = useState(false);
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    try {
      const packets = await getMessagePackets(50);
      const found = packets.find((p) => p.id === alertId) ?? null;
      setPacket(found);
      if (found?.is_false_alarm) setDecision("not_a_threat");
    } catch {
      // leave packet null -- shows "not found" state below
    } finally {
      setLoading(false);
    }
  }, [alertId]);

  useEffect(() => {
    load();
  }, [load]);

  const onNotAThreat = async () => {
    setMarking(true);
    try {
      await markFalseAlarm(alertId);
      setDecision("not_a_threat");
    } catch (e) {
      RNAlert.alert("Failed", e instanceof Error ? e.message : "Could not update alert.");
    } finally {
      setMarking(false);
    }
  };

  const onNotifyCommunity = async () => {
    setSending(true);
    try {
      const res = await sendMessagePacket(alertId);
      RNAlert.alert(
        "Community notified",
        `Delivered to ${res.sent} community member(s)${res.failed ? `, ${res.failed} failed` : ""}.`
      );
    } catch (e) {
      RNAlert.alert("Failed to send", e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSending(false);
    }
  };

  if (!user) return null;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Take a Look</Text>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={styles.closeButton}>Close</Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <ActivityIndicator size="large" color="#fff" style={styles.loading} />
      ) : !packet ? (
        <View style={styles.loading}>
          <Text style={styles.notFoundText}>
            No screenshot found for this alert (it may predate the message-packet feature).
          </Text>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {packet.screenshot_url ? (
            <Image source={{ uri: authenticatedFileUrl(packet.screenshot_url, user.token) }} style={styles.image} />
          ) : (
            <View style={[styles.image, styles.noImage]}>
              <Text style={styles.noImageText}>No camera snapshot for this report</Text>
            </View>
          )}

          <Text style={styles.alertType}>{packet.alert_type.replace(/-/g, " ")}</Text>

          <View style={styles.confidenceCard}>
            <Text style={styles.confidenceLabel}>
              {packet.alert_type === "peer-reported" ? "Reported by a community member" : "Model prediction confidence"}
            </Text>
            <Text style={styles.confidenceValue}>{(packet.confidence * 100).toFixed(0)}%</Text>
          </View>

          <View style={styles.metaRow}>
            <Text style={styles.metaText}>{packet.timestamp}</Text>
            <Text style={styles.metaText}>Reported by {packet.operator_username}</Text>
          </View>

          <Text style={styles.sectionLabel}>Location</Text>
          <View style={styles.mapContainer}>
            <WebView
              source={{
                html: buildMapHtml([
                  {
                    id: "device",
                    lat: packet.location.lat,
                    lng: packet.location.lng,
                    label: packet.location.label,
                    kind: "device",
                  },
                ]),
              }}
              style={styles.map}
            />
          </View>
          <Text style={styles.locationText}>
            {packet.location.label} ({packet.location.lat}, {packet.location.lng})
          </Text>

          {decision === "pending" && (
            <View style={styles.decisionRow}>
              <TouchableOpacity style={styles.notThreatButton} onPress={onNotAThreat} disabled={marking}>
                {marking ? <ActivityIndicator color="#fff" /> : <Text style={styles.notThreatButtonText}>Not a Threat</Text>}
              </TouchableOpacity>
              <TouchableOpacity style={styles.threatButton} onPress={() => setDecision("confirmed_threat")}>
                <Text style={styles.threatButtonText}>This is a Threat</Text>
              </TouchableOpacity>
            </View>
          )}

          {decision === "not_a_threat" && (
            <View style={styles.resultBanner}>
              <Text style={styles.resultBannerText}>Marked as false alarm — no action needed.</Text>
            </View>
          )}

          {decision === "confirmed_threat" && (
            <View>
              <View style={[styles.resultBanner, styles.threatBanner]}>
                <Text style={styles.resultBannerText}>
                  Confirmed as a real threat. Notify the {packet.recipients.length} community member(s)?
                </Text>
              </View>
              <TouchableOpacity style={styles.notifyButton} onPress={onNotifyCommunity} disabled={sending}>
                {sending ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.notifyButtonText}>Notify Community ({packet.recipients.length})</Text>
                )}
              </TouchableOpacity>
            </View>
          )}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 16,
    paddingTop: 50,
  },
  title: { color: "#fff", fontSize: 20, fontWeight: "700" },
  closeButton: { color: "#60a5fa", fontSize: 16, fontWeight: "600" },
  loading: { flex: 1, justifyContent: "center", alignItems: "center", padding: 24 },
  notFoundText: { color: "#64748b", textAlign: "center" },
  scrollContent: { padding: 16, paddingTop: 0 },
  image: { width: "100%", aspectRatio: 4 / 3, borderRadius: 12, backgroundColor: "#000", marginBottom: 16 },
  noImage: { justifyContent: "center", alignItems: "center", backgroundColor: "#1e293b" },
  noImageText: { color: "#64748b", fontSize: 13 },
  alertType: { color: "#fff", fontSize: 22, fontWeight: "700", textTransform: "capitalize", marginBottom: 12 },
  confidenceCard: {
    backgroundColor: "#1e293b",
    borderRadius: 10,
    padding: 16,
    alignItems: "center",
    marginBottom: 16,
  },
  confidenceLabel: { color: "#94a3b8", fontSize: 12, textTransform: "uppercase", marginBottom: 4 },
  confidenceValue: { color: "#fff", fontSize: 32, fontWeight: "800" },
  metaRow: { flexDirection: "row", justifyContent: "space-between", marginBottom: 16 },
  metaText: { color: "#94a3b8", fontSize: 12 },
  sectionLabel: { color: "#64748b", fontSize: 12, textTransform: "uppercase", marginBottom: 4 },
  mapContainer: { height: 160, borderRadius: 10, overflow: "hidden", marginBottom: 6 },
  map: { flex: 1 },
  locationText: { color: "#e2e8f0", fontSize: 14, marginBottom: 24 },
  decisionRow: { flexDirection: "row", gap: 12 },
  notThreatButton: {
    flex: 1,
    backgroundColor: "#334155",
    borderRadius: 10,
    paddingVertical: 16,
    alignItems: "center",
  },
  notThreatButtonText: { color: "#e2e8f0", fontWeight: "700" },
  threatButton: { flex: 1, backgroundColor: "#dc2626", borderRadius: 10, paddingVertical: 16, alignItems: "center" },
  threatButtonText: { color: "#fff", fontWeight: "700" },
  resultBanner: { backgroundColor: "#1e293b", borderRadius: 10, padding: 16, marginBottom: 16 },
  threatBanner: { borderColor: "#dc2626", borderWidth: 1 },
  resultBannerText: { color: "#e2e8f0", fontSize: 14 },
  notifyButton: { backgroundColor: "#dc2626", borderRadius: 10, paddingVertical: 16, alignItems: "center" },
  notifyButtonText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
