import React, { useCallback, useEffect, useState } from "react";
import { View, Text, TouchableOpacity, StyleSheet, FlatList, RefreshControl } from "react-native";
import { getUsers, deleteUser } from "../api/users";
import { UserItem } from "../types";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";

export default function UsersScreen() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<UserItem[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setUsers(await getUsers());
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

  const onDelete = async (id: number) => {
    setError(null);
    try {
      await deleteUser(id);
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not delete user.");
    }
  };

  return (
    <FlatList
      style={styles.container}
      data={users}
      keyExtractor={(item) => String(item.id)}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#fff" />}
      ListHeaderComponent={
        <View>
          <Text style={styles.header}>Users</Text>
          {error && <Text style={styles.error}>{error}</Text>}
        </View>
      }
      ListEmptyComponent={<Text style={styles.emptyText}>No users found.</Text>}
      renderItem={({ item }) => (
        <View style={styles.row}>
          <View style={styles.rowMain}>
            <Text style={styles.username}>
              {item.username} <Text style={styles.role}>· {item.role}</Text>
            </Text>
            {item.email && <Text style={styles.email}>{item.email}</Text>}
          </View>
          {item.username !== currentUser?.username && (
            <TouchableOpacity style={styles.deleteButton} onPress={() => onDelete(item.id)}>
              <Text style={styles.deleteButtonText}>Delete</Text>
            </TouchableOpacity>
          )}
        </View>
      )}
    />
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  header: { color: "#fff", fontSize: 20, fontWeight: "700", padding: 16, paddingTop: 20 },
  error: { color: "#f87171", paddingHorizontal: 16, marginBottom: 8 },
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
  username: { color: "#fff", fontWeight: "700" },
  role: { color: "#94a3b8", fontWeight: "400" },
  email: { color: "#94a3b8", fontSize: 12, marginTop: 2 },
  deleteButton: { backgroundColor: "#7f1d1d", paddingHorizontal: 10, paddingVertical: 6, borderRadius: 6 },
  deleteButtonText: { color: "#fecaca", fontSize: 12, fontWeight: "600" },
  emptyText: { color: "#64748b", textAlign: "center", marginTop: 40 },
});
