import React, { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  TextInput,
  Image,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Modal,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from "react-native";
import { WebView } from "react-native-webview";
import { useAuth } from "../context/AuthContext";
import { authenticatedFileUrl } from "../api/client";
import { getMessagePackets, sendMessagePacket } from "../api/messagePackets";
import { getDeviceLocation, updateDeviceLocation } from "../api/deviceLocation";
import { buildMapHtml } from "../maps/mapHtml";
import { MessagePacket, DeviceLocation } from "../types";

export default function CommunityScreen() {
  const { user } = useAuth();
  const isAdmin = user?.role === "Admin";
  const [packets, setPackets] = useState<MessagePacket[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [selected, setSelected] = useState<MessagePacket | null>(null);
  const [sending, setSending] = useState(false);

  const [location, setLocation] = useState<DeviceLocation | null>(null);
  const [editingLocation, setEditingLocation] = useState(false);
  const [locationForm, setLocationForm] = useState({ label: "", lat: "", lng: "" });
  const [locationError, setLocationError] = useState<string | null>(null);
  const [savingLocation, setSavingLocation] = useState(false);

  const load = useCallback(async () => {
    try {
      setPackets(await getMessagePackets(30));
    } catch {
      // keep last-known list; pull-to-refresh retries
    }
    try {
      setLocation(await getDeviceLocation());
    } catch {
      // keep last-known location
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  const openEditLocation = () => {
    if (location) {
      setLocationForm({ label: location.label, lat: String(location.lat), lng: String(location.lng) });
    }
    setLocationError(null);
    setEditingLocation(true);
  };

  const onSaveLocation = async () => {
    setLocationError(null);
    const lat = Number(locationForm.lat);
    const lng = Number(locationForm.lng);
    if (!locationForm.label || Number.isNaN(lat) || Number.isNaN(lng)) {
      setLocationError("Enter a label and numeric lat/lng.");
      return;
    }
    setSavingLocation(true);
    try {
      setLocation(await updateDeviceLocation(locationForm.label, lat, lng));
      setEditingLocation(false);
    } catch (e) {
      setLocationError(e instanceof Error ? e.message : "Could not save location.");
    } finally {
      setSavingLocation(false);
    }
  };

  const onSend = async () => {
    if (!selected) return;
    setSending(true);
    try {
      const res = await sendMessagePacket(selected.id);
      Alert.alert("Sent", `Delivered to ${res.sent} community member(s)${res.failed ? `, ${res.failed} failed` : ""}.`);
    } catch (e) {
      Alert.alert("Failed to send", e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSending(false);
    }
  };

  if (!user) return null;

  return (
    <View style={styles.container}>
      <FlatList
        data={packets}
        keyExtractor={(item) => String(item.id)}
        numColumns={2}
        contentContainerStyle={packets.length === 0 && styles.emptyContainer}
        columnWrapperStyle={styles.row}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#fff" />}
        ListHeaderComponent={
          <View style={styles.locationHeader}>
            <View style={styles.locationHeaderText}>
              <Text style={styles.locationHeaderLabel}>Camera Location</Text>
              <Text style={styles.locationHeaderValue}>
                {location ? `${location.label} (${location.lat}, ${location.lng})` : "Loading…"}
              </Text>
            </View>
            {isAdmin && (
              <TouchableOpacity style={styles.locationEditButton} onPress={openEditLocation}>
                <Text style={styles.locationEditButtonText}>Edit</Text>
              </TouchableOpacity>
            )}
          </View>
        }
        ListEmptyComponent={<Text style={styles.emptyText}>No message packets yet.</Text>}
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.card} onPress={() => setSelected(item)}>
            {item.screenshot_url ? (
              <Image source={{ uri: authenticatedFileUrl(item.screenshot_url, user.token) }} style={styles.thumb} />
            ) : (
              <View style={[styles.thumb, styles.noThumb]}>
                <Text style={styles.noThumbText}>No snapshot</Text>
              </View>
            )}
            <Text style={styles.cardType}>{item.alert_type.replace(/-/g, " ")}</Text>
            <Text style={styles.cardMeta}>{item.timestamp.split(" ")[1]}</Text>
          </TouchableOpacity>
        )}
      />

      <Modal visible={!!selected} animationType="slide" onRequestClose={() => setSelected(null)}>
        {selected && (
          <View style={styles.modalContainer}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>{selected.alert_type.replace(/-/g, " ")}</Text>
              <TouchableOpacity onPress={() => setSelected(null)}>
                <Text style={styles.closeButton}>Close</Text>
              </TouchableOpacity>
            </View>

            {selected.screenshot_url ? (
              <Image
                source={{ uri: authenticatedFileUrl(selected.screenshot_url, user.token) }}
                style={styles.fullImage}
              />
            ) : (
              <View style={[styles.fullImage, styles.noThumb]}>
                <Text style={styles.noThumbText}>No camera snapshot for this report</Text>
              </View>
            )}

            <Text style={styles.sectionLabel}>Location</Text>
            <View style={styles.mapContainer}>
              <WebView
                source={{
                  html: buildMapHtml([
                    {
                      id: "device",
                      lat: selected.location.lat,
                      lng: selected.location.lng,
                      label: selected.location.label,
                      kind: "device",
                    },
                  ]),
                }}
                style={styles.map}
              />
            </View>
            <Text style={styles.locationLabel}>{selected.location.label}</Text>

            <Text style={styles.sectionLabel}>Recipients ({selected.recipients.length})</Text>
            <Text style={styles.recipientsText}>
              {selected.recipients.map((r) => r.name).join(", ")}
            </Text>

            <TouchableOpacity style={styles.sendButton} onPress={onSend} disabled={sending}>
              {sending ? <ActivityIndicator color="#fff" /> : <Text style={styles.sendButtonText}>Send to Community</Text>}
            </TouchableOpacity>
          </View>
        )}
      </Modal>

      <Modal visible={editingLocation} animationType="slide" transparent onRequestClose={() => setEditingLocation(false)}>
        <View style={styles.editOverlay}>
          <View style={styles.editCard}>
            <Text style={styles.modalTitle}>Edit Camera Location</Text>

            <TextInput
              style={styles.input}
              placeholder="Label (e.g. Main Gate Camera)"
              placeholderTextColor="#64748b"
              value={locationForm.label}
              onChangeText={(v) => setLocationForm((f) => ({ ...f, label: v }))}
            />
            <TextInput
              style={styles.input}
              placeholder="Latitude"
              placeholderTextColor="#64748b"
              keyboardType="numbers-and-punctuation"
              value={locationForm.lat}
              onChangeText={(v) => setLocationForm((f) => ({ ...f, lat: v }))}
            />
            <TextInput
              style={styles.input}
              placeholder="Longitude"
              placeholderTextColor="#64748b"
              keyboardType="numbers-and-punctuation"
              value={locationForm.lng}
              onChangeText={(v) => setLocationForm((f) => ({ ...f, lng: v }))}
            />

            {locationError && <Text style={styles.locationError}>{locationError}</Text>}

            <View style={styles.editButtonRow}>
              <TouchableOpacity style={styles.cancelButton} onPress={() => setEditingLocation(false)}>
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.saveButton} onPress={onSaveLocation} disabled={savingLocation}>
                {savingLocation ? <ActivityIndicator color="#fff" /> : <Text style={styles.saveButtonText}>Save</Text>}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  row: { justifyContent: "space-between", paddingHorizontal: 12 },
  card: { backgroundColor: "#1e293b", borderRadius: 10, padding: 8, marginBottom: 12, width: "48%" },
  thumb: { width: "100%", aspectRatio: 4 / 3, borderRadius: 6, marginBottom: 6, backgroundColor: "#0f172a" },
  noThumb: { justifyContent: "center", alignItems: "center" },
  noThumbText: { color: "#64748b", fontSize: 11, textAlign: "center", paddingHorizontal: 8 },
  cardType: { color: "#fff", fontWeight: "700", fontSize: 13, textTransform: "capitalize" },
  cardMeta: { color: "#94a3b8", fontSize: 11, marginTop: 2 },
  emptyContainer: { flexGrow: 1, justifyContent: "center", alignItems: "center" },
  emptyText: { color: "#64748b", textAlign: "center" },
  modalContainer: { flex: 1, backgroundColor: "#0f172a", padding: 16, paddingTop: 50 },
  modalHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 16 },
  modalTitle: { color: "#fff", fontSize: 20, fontWeight: "700", textTransform: "capitalize" },
  closeButton: { color: "#60a5fa", fontSize: 16, fontWeight: "600" },
  fullImage: { width: "100%", aspectRatio: 4 / 3, borderRadius: 10, backgroundColor: "#000", marginBottom: 16 },
  sectionLabel: { color: "#64748b", fontSize: 12, marginBottom: 6, textTransform: "uppercase" },
  mapContainer: { height: 180, borderRadius: 10, overflow: "hidden", marginBottom: 4 },
  map: { flex: 1 },
  locationLabel: { color: "#94a3b8", fontSize: 12, marginBottom: 16 },
  recipientsText: { color: "#e2e8f0", fontSize: 14, marginBottom: 24 },
  sendButton: { backgroundColor: "#dc2626", borderRadius: 10, paddingVertical: 16, alignItems: "center" },
  sendButtonText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  locationHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "#1e293b",
    borderRadius: 10,
    padding: 14,
    marginHorizontal: 12,
    marginTop: 16,
    marginBottom: 8,
  },
  locationHeaderText: { flex: 1, paddingRight: 8 },
  locationHeaderLabel: { color: "#64748b", fontSize: 11, textTransform: "uppercase", marginBottom: 2 },
  locationHeaderValue: { color: "#fff", fontSize: 13, fontWeight: "600" },
  locationEditButton: { backgroundColor: "#2563eb", paddingHorizontal: 14, paddingVertical: 8, borderRadius: 8 },
  locationEditButtonText: { color: "#fff", fontWeight: "700", fontSize: 12 },
  editOverlay: { flex: 1, backgroundColor: "rgba(0,0,0,0.6)", justifyContent: "center", padding: 20 },
  editCard: { backgroundColor: "#1e293b", borderRadius: 14, padding: 20 },
  input: {
    backgroundColor: "#0f172a",
    color: "#fff",
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginTop: 12,
  },
  locationError: { color: "#f87171", marginTop: 10 },
  editButtonRow: { flexDirection: "row", justifyContent: "flex-end", gap: 10, marginTop: 20 },
  cancelButton: { paddingHorizontal: 16, paddingVertical: 12, borderRadius: 8 },
  cancelButtonText: { color: "#94a3b8", fontWeight: "600" },
  saveButton: { backgroundColor: "#2563eb", paddingHorizontal: 20, paddingVertical: 12, borderRadius: 8 },
  saveButtonText: { color: "#fff", fontWeight: "700" },
});
