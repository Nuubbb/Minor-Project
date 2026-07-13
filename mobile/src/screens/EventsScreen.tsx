import React, { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  RefreshControl,
} from "react-native";
import { getEvents, addEvent, deleteEvent } from "../api/events";
import { EventItem } from "../types";
import { ApiError } from "../api/client";

export default function EventsScreen() {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [form, setForm] = useState({ event_date: "", name: "", start_hour: "", end_hour: "", expected_crowd: "" });
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setEvents(await getEvents());
    } catch {
      // keep last-known list; pull-to-refresh retries
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

  const onAdd = async () => {
    setError(null);
    const { event_date, name, start_hour, end_hour, expected_crowd } = form;
    if (!event_date || !name || !start_hour || !end_hour || !expected_crowd) {
      setError("All fields are required.");
      return;
    }
    try {
      await addEvent({
        event_date,
        name,
        start_hour: Number(start_hour),
        end_hour: Number(end_hour),
        expected_crowd: Number(expected_crowd),
      });
      setForm({ event_date: "", name: "", start_hour: "", end_hour: "", expected_crowd: "" });
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not add event.");
    }
  };

  const onDelete = async (id: number) => {
    setEvents((prev) => prev.filter((e) => e.id !== id));
    try {
      await deleteEvent(id);
    } catch {
      load();
    }
  };

  return (
    <FlatList
      style={styles.container}
      data={events}
      keyExtractor={(item) => String(item.id)}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#fff" />}
      ListHeaderComponent={
        <View>
          <Text style={styles.header}>Scheduled Events</Text>
          <View style={styles.form}>
            <TextInput
              style={styles.input}
              placeholder="Date (YYYY-MM-DD)"
              placeholderTextColor="#64748b"
              value={form.event_date}
              onChangeText={(v) => setForm((f) => ({ ...f, event_date: v }))}
            />
            <TextInput
              style={styles.input}
              placeholder="Event name"
              placeholderTextColor="#64748b"
              value={form.name}
              onChangeText={(v) => setForm((f) => ({ ...f, name: v }))}
            />
            <View style={styles.row}>
              <TextInput
                style={[styles.input, styles.rowInput]}
                placeholder="Start hour (0-23)"
                placeholderTextColor="#64748b"
                keyboardType="number-pad"
                value={form.start_hour}
                onChangeText={(v) => setForm((f) => ({ ...f, start_hour: v }))}
              />
              <TextInput
                style={[styles.input, styles.rowInput]}
                placeholder="End hour (0-23)"
                placeholderTextColor="#64748b"
                keyboardType="number-pad"
                value={form.end_hour}
                onChangeText={(v) => setForm((f) => ({ ...f, end_hour: v }))}
              />
            </View>
            <TextInput
              style={styles.input}
              placeholder="Expected crowd"
              placeholderTextColor="#64748b"
              keyboardType="number-pad"
              value={form.expected_crowd}
              onChangeText={(v) => setForm((f) => ({ ...f, expected_crowd: v }))}
            />
            {error && <Text style={styles.error}>{error}</Text>}
            <TouchableOpacity style={styles.addButton} onPress={onAdd}>
              <Text style={styles.addButtonText}>Schedule Event</Text>
            </TouchableOpacity>
          </View>
        </View>
      }
      ListEmptyComponent={<Text style={styles.emptyText}>No events scheduled.</Text>}
      renderItem={({ item }) => (
        <View style={styles.eventRow}>
          <View style={styles.eventMain}>
            <Text style={styles.eventName}>{item.name}</Text>
            <Text style={styles.eventMeta}>
              {item.event_date} · {item.start_hour}:00–{item.end_hour}:00 · crowd ~{item.expected_crowd}
            </Text>
          </View>
          <TouchableOpacity style={styles.deleteButton} onPress={() => onDelete(item.id)}>
            <Text style={styles.deleteButtonText}>Delete</Text>
          </TouchableOpacity>
        </View>
      )}
    />
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  header: { color: "#fff", fontSize: 20, fontWeight: "700", padding: 16, paddingTop: 20 },
  form: { paddingHorizontal: 16, marginBottom: 8 },
  input: {
    backgroundColor: "#1e293b",
    color: "#fff",
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
    marginBottom: 10,
  },
  row: { flexDirection: "row", gap: 10 },
  rowInput: { flex: 1 },
  error: { color: "#f87171", marginBottom: 10 },
  addButton: { backgroundColor: "#2563eb", borderRadius: 8, paddingVertical: 12, alignItems: "center" },
  addButtonText: { color: "#fff", fontWeight: "700" },
  eventRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "#1e293b",
    borderRadius: 8,
    padding: 12,
    marginHorizontal: 16,
    marginVertical: 6,
  },
  eventMain: { flex: 1, paddingRight: 8 },
  eventName: { color: "#fff", fontWeight: "700", marginBottom: 4 },
  eventMeta: { color: "#94a3b8", fontSize: 12 },
  deleteButton: { backgroundColor: "#7f1d1d", paddingHorizontal: 10, paddingVertical: 6, borderRadius: 6 },
  deleteButtonText: { color: "#fecaca", fontSize: 12, fontWeight: "600" },
  emptyText: { color: "#64748b", textAlign: "center", marginTop: 40 },
});
