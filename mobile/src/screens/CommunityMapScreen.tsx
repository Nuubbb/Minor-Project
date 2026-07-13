import React, { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Modal,
  ActivityIndicator,
  Alert as RNAlert,
} from "react-native";
import { WebView, WebViewMessageEvent } from "react-native-webview";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useNavigation } from "@react-navigation/native";
import { useAuth } from "../context/AuthContext";
import { getDeviceLocation } from "../api/deviceLocation";
import { getCommunity } from "../api/messagePackets";
import { createPeerReport } from "../api/peerReports";
import { buildMapHtml, MapPin } from "../maps/mapHtml";
import { CommunityMember, DeviceLocation } from "../types";
import type { RootStackParamList } from "../navigation/types";

export default function CommunityMapScreen() {
  const { user } = useAuth();
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();

  const [location, setLocation] = useState<DeviceLocation | null>(null);
  const [members, setMembers] = useState<CommunityMember[]>([]);
  const [selected, setSelected] = useState<CommunityMember | null>(null);
  const [reporting, setReporting] = useState(false);
  const [reportMessage, setReportMessage] = useState("");
  const [sendingReport, setSendingReport] = useState(false);

  const load = useCallback(async () => {
    try {
      const [loc, mem] = await Promise.all([getDeviceLocation(), getCommunity()]);
      setLocation(loc);
      setMembers(mem);
    } catch {
      // keep last-known state; screen will just look empty until next mount
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (!user || !location) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#fff" />
      </View>
    );
  }

  const pins: MapPin[] = [
    { id: "device", lat: location.lat, lng: location.lng, label: location.label, subtitle: "This device", kind: "device" },
    ...members
      .filter((m) => m.lat !== null && m.lng !== null)
      .map((m) => ({
        id: m.id,
        lat: m.lat as number,
        lng: m.lng as number,
        label: m.name,
        subtitle: "Tap to view options",
        kind: "member" as const,
        tappable: true,
      })),
  ];

  const onMessage = (event: WebViewMessageEvent) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      if (data.type === "pinTap" && data.id !== "device") {
        const member = members.find((m) => m.id === data.id);
        if (member) {
          setSelected(member);
          setReporting(false);
          setReportMessage("");
        }
      }
    } catch {
      // ignore malformed messages
    }
  };

  const closeSheet = () => {
    setSelected(null);
    setReporting(false);
  };

  const onViewCamera = () => {
    if (!selected) return;
    const memberName = selected.name;
    closeSheet();
    navigation.navigate("MemberCamera", { memberId: selected.id, memberName });
  };

  const onSendReport = async () => {
    if (!selected) return;
    setSendingReport(true);
    try {
      await createPeerReport(selected.id, reportMessage || undefined);
      RNAlert.alert("Report sent", `${selected.name} will be notified to review this.`);
      closeSheet();
    } catch (e) {
      RNAlert.alert("Failed to send", e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSendingReport(false);
    }
  };

  return (
    <View style={styles.container}>
      <WebView source={{ html: buildMapHtml(pins, { zoom: 15 }) }} onMessage={onMessage} style={styles.map} />

      <Modal visible={!!selected} animationType="slide" transparent onRequestClose={closeSheet}>
        <TouchableOpacity style={styles.sheetOverlay} activeOpacity={1} onPress={closeSheet}>
          <TouchableOpacity activeOpacity={1} style={styles.sheet} onPress={(e) => e.stopPropagation()}>
            {selected && (
              <>
                <View style={styles.sheetHandle} />
                <Text style={styles.sheetName}>{selected.name}</Text>
                <Text style={styles.sheetDetail}>{selected.phone ?? "No phone on file"}</Text>
                <Text style={styles.sheetDetail}>{selected.email}</Text>
                <Text style={styles.sheetDetail}>
                  {selected.lat}, {selected.lng}
                </Text>

                {!reporting ? (
                  <View style={styles.sheetActions}>
                    <TouchableOpacity style={styles.viewCameraButton} onPress={onViewCamera}>
                      <Text style={styles.viewCameraButtonText}>View Camera</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.alertOwnerButton} onPress={() => setReporting(true)}>
                      <Text style={styles.alertOwnerButtonText}>Alert Owner</Text>
                    </TouchableOpacity>
                  </View>
                ) : (
                  <View style={styles.reportForm}>
                    <Text style={styles.reportLabel}>
                      Report suspicious activity to {selected.name}?
                    </Text>
                    <TextInput
                      style={styles.reportInput}
                      placeholder="What did you see? (optional)"
                      placeholderTextColor="#64748b"
                      value={reportMessage}
                      onChangeText={setReportMessage}
                      multiline
                    />
                    <View style={styles.sheetActions}>
                      <TouchableOpacity style={styles.cancelButton} onPress={() => setReporting(false)}>
                        <Text style={styles.cancelButtonText}>Cancel</Text>
                      </TouchableOpacity>
                      <TouchableOpacity style={styles.sendReportButton} onPress={onSendReport} disabled={sendingReport}>
                        {sendingReport ? (
                          <ActivityIndicator color="#fff" />
                        ) : (
                          <Text style={styles.sendReportButtonText}>Send Report</Text>
                        )}
                      </TouchableOpacity>
                    </View>
                  </View>
                )}
              </>
            )}
          </TouchableOpacity>
        </TouchableOpacity>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  loadingContainer: { flex: 1, backgroundColor: "#0f172a", justifyContent: "center", alignItems: "center" },
  map: { flex: 1 },
  sheetOverlay: { flex: 1, backgroundColor: "rgba(0,0,0,0.5)", justifyContent: "flex-end" },
  sheet: { backgroundColor: "#1e293b", borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, paddingBottom: 32 },
  sheetHandle: { width: 40, height: 4, borderRadius: 2, backgroundColor: "#475569", alignSelf: "center", marginBottom: 16 },
  sheetName: { color: "#fff", fontSize: 20, fontWeight: "700", marginBottom: 6 },
  sheetDetail: { color: "#94a3b8", fontSize: 13, marginBottom: 2 },
  sheetActions: { flexDirection: "row", gap: 10, marginTop: 20 },
  viewCameraButton: { flex: 1, backgroundColor: "#2563eb", borderRadius: 10, paddingVertical: 14, alignItems: "center" },
  viewCameraButtonText: { color: "#fff", fontWeight: "700" },
  alertOwnerButton: { flex: 1, backgroundColor: "#dc2626", borderRadius: 10, paddingVertical: 14, alignItems: "center" },
  alertOwnerButtonText: { color: "#fff", fontWeight: "700" },
  reportForm: { marginTop: 16 },
  reportLabel: { color: "#e2e8f0", fontSize: 14, marginBottom: 10 },
  reportInput: {
    backgroundColor: "#0f172a",
    color: "#fff",
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
    minHeight: 70,
    textAlignVertical: "top",
  },
  cancelButton: { flex: 1, paddingVertical: 14, alignItems: "center" },
  cancelButtonText: { color: "#94a3b8", fontWeight: "600" },
  sendReportButton: { flex: 1, backgroundColor: "#dc2626", borderRadius: 10, paddingVertical: 14, alignItems: "center" },
  sendReportButtonText: { color: "#fff", fontWeight: "700" },
});
