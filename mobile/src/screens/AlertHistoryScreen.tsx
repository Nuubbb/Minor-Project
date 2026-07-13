import React, { useCallback, useEffect, useState } from "react";
import { View, Text, StyleSheet } from "react-native";
import { getAlertHistory } from "../api/alerts";
import { Alert } from "../types";
import AlertList from "../components/AlertList";

export default function AlertHistoryScreen() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await getAlertHistory();
      setAlerts(data);
    } catch {
      // keep whatever was last loaded; user can pull-to-refresh
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

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Alert History</Text>
      <AlertList alerts={alerts} refreshing={refreshing} onRefresh={onRefresh} emptyLabel="No alerts recorded yet." />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  header: { color: "#fff", fontSize: 20, fontWeight: "700", padding: 16, paddingTop: 20 },
});
