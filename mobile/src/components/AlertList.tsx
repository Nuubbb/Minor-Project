import React from "react";
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl } from "react-native";
import { Alert } from "../types";

interface Props {
  alerts: Alert[];
  onMarkFalse?: (alertId: number) => void;
  refreshing?: boolean;
  onRefresh?: () => void;
  emptyLabel?: string;
}

export default function AlertList({ alerts, onMarkFalse, refreshing, onRefresh, emptyLabel }: Props) {
  return (
    <FlatList
      data={alerts}
      keyExtractor={(item) => String(item.id)}
      contentContainerStyle={alerts.length === 0 && styles.emptyContainer}
      refreshControl={
        onRefresh ? <RefreshControl refreshing={!!refreshing} onRefresh={onRefresh} tintColor="#fff" /> : undefined
      }
      ListEmptyComponent={<Text style={styles.emptyText}>{emptyLabel ?? "No security events logged."}</Text>}
      renderItem={({ item }) => (
        <View style={styles.row}>
          <View style={styles.rowMain}>
            <Text style={styles.type}>{item.alert_type.replace(/-/g, " ")}</Text>
            <Text style={styles.meta}>
              {item.timestamp} · {(item.confidence * 100).toFixed(0)}% · {item.operator_username}
            </Text>
          </View>
          {item.is_false_alarm ? (
            <Text style={styles.dismissed}>Dismissed</Text>
          ) : (
            <View style={styles.rowActions}>
              <Text style={styles.active}>Active</Text>
              {onMarkFalse && (
                <TouchableOpacity style={styles.markButton} onPress={() => onMarkFalse(item.id)}>
                  <Text style={styles.markButtonText}>Mark False</Text>
                </TouchableOpacity>
              )}
            </View>
          )}
        </View>
      )}
    />
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "#1e293b",
    borderRadius: 8,
    padding: 12,
    marginHorizontal: 16,
    marginVertical: 6,
  },
  rowMain: { flex: 1, paddingRight: 8 },
  type: { color: "#fff", fontWeight: "700", textTransform: "capitalize", marginBottom: 4 },
  meta: { color: "#94a3b8", fontSize: 12 },
  rowActions: { alignItems: "flex-end" },
  active: { color: "#f87171", fontWeight: "700", fontSize: 12, marginBottom: 6 },
  dismissed: { color: "#64748b", fontWeight: "700", fontSize: 12 },
  markButton: { backgroundColor: "#334155", paddingHorizontal: 10, paddingVertical: 6, borderRadius: 6 },
  markButtonText: { color: "#e2e8f0", fontSize: 11, fontWeight: "600" },
  emptyContainer: { flexGrow: 1, justifyContent: "center", alignItems: "center" },
  emptyText: { color: "#64748b", textAlign: "center", marginTop: 40 },
});
