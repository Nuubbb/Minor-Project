import React from "react";
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl } from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { Alert } from "../types";
import type { RootStackParamList } from "../navigation/types";

interface Props {
  alerts: Alert[];
  refreshing?: boolean;
  onRefresh?: () => void;
  emptyLabel?: string;
}

export default function AlertList({ alerts, refreshing, onRefresh, emptyLabel }: Props) {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();

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
          <View style={styles.rowActions}>
            {item.is_false_alarm ? (
              <Text style={styles.dismissed}>Dismissed</Text>
            ) : (
              <Text style={styles.active}>Active</Text>
            )}
            <TouchableOpacity
              style={styles.lookButton}
              onPress={() => navigation.navigate("AlertValidator", { alertId: item.id })}
            >
              <Text style={styles.lookButtonText}>Take a look</Text>
            </TouchableOpacity>
          </View>
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
  dismissed: { color: "#64748b", fontWeight: "700", fontSize: 12, marginBottom: 6 },
  lookButton: { backgroundColor: "#2563eb", paddingHorizontal: 10, paddingVertical: 6, borderRadius: 6 },
  lookButtonText: { color: "#fff", fontSize: 11, fontWeight: "600" },
  emptyContainer: { flexGrow: 1, justifyContent: "center", alignItems: "center" },
  emptyText: { color: "#64748b", textAlign: "center", marginTop: 40 },
});
