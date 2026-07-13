import React from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { useAuth } from "../context/AuthContext";

export default function ProfileScreen() {
  const { user, logout } = useAuth();

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.label}>Username</Text>
        <Text style={styles.value}>{user?.username}</Text>
        <Text style={styles.label}>Role</Text>
        <Text style={styles.value}>{user?.role}</Text>
        <Text style={styles.label}>Email</Text>
        <Text style={styles.value}>{user?.email ?? "—"}</Text>
      </View>
      <TouchableOpacity style={styles.logoutButton} onPress={logout}>
        <Text style={styles.logoutButtonText}>Log Out</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a", padding: 16, paddingTop: 20 },
  card: { backgroundColor: "#1e293b", borderRadius: 12, padding: 16, marginBottom: 24 },
  label: { color: "#64748b", fontSize: 12, marginTop: 10 },
  value: { color: "#fff", fontSize: 16, fontWeight: "600" },
  logoutButton: { backgroundColor: "#7f1d1d", borderRadius: 8, paddingVertical: 14, alignItems: "center" },
  logoutButtonText: { color: "#fecaca", fontWeight: "700", fontSize: 16 },
});
