import React, { useCallback, useEffect, useRef, useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import type { BottomTabScreenProps } from "@react-navigation/bottom-tabs";
import { useAuth } from "../context/AuthContext";
import { getAlerts, markFalseAlarm } from "../api/alerts";
import { Alert } from "../types";
import AlertList from "../components/AlertList";
import type { MainTabParamList } from "../navigation/types";

const POLL_MS = 3000;

type Props = BottomTabScreenProps<MainTabParamList, "Dashboard">;

export default function DashboardScreen({ navigation }: Props) {
  const { user } = useAuth();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await getAlerts(50);
      setAlerts(data);
    } catch {
      // silent: the poll will retry on the next tick
    }
  }, []);

  useEffect(() => {
    load();
    intervalRef.current = setInterval(load, POLL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [load]);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  const onMarkFalse = async (alertId: number) => {
    setAlerts((prev) => prev.map((a) => (a.id === alertId ? { ...a, is_false_alarm: true } : a)));
    try {
      await markFalseAlarm(alertId);
    } catch {
      load();
    }
  };

  const activeCount = alerts.filter((a) => !a.is_false_alarm).length;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Hi, {user?.username}</Text>
          <Text style={styles.subtitle}>
            {activeCount} active {activeCount === 1 ? "alert" : "alerts"}
          </Text>
        </View>
        <TouchableOpacity style={styles.liveButton} onPress={() => navigation.navigate("Live")}>
          <Text style={styles.liveButtonText}>Live Camera</Text>
        </TouchableOpacity>
      </View>

      <AlertList alerts={alerts} onMarkFalse={onMarkFalse} refreshing={refreshing} onRefresh={onRefresh} />
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
    paddingTop: 20,
  },
  greeting: { color: "#fff", fontSize: 20, fontWeight: "700" },
  subtitle: { color: "#94a3b8", fontSize: 13, marginTop: 2 },
  liveButton: { backgroundColor: "#dc2626", borderRadius: 8, paddingHorizontal: 14, paddingVertical: 10 },
  liveButtonText: { color: "#fff", fontWeight: "700", fontSize: 13 },
});
