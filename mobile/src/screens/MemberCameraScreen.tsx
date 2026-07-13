import React, { useState } from "react";
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity } from "react-native";
import { WebView } from "react-native-webview";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useAuth } from "../context/AuthContext";
import { videoFeedUrl } from "../api/client";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "MemberCamera">;

function buildHtml(url: string) {
  return `<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
  <style>html,body{margin:0;padding:0;background:#000;height:100%;}
  img{width:100%;height:100%;object-fit:contain;}</style></head>
  <body><img src="${url}" /></body></html>`;
}

// There's only one physical camera in this system right now -- every
// member's "camera" is this same feed, just labeled with their name, until
// there's real per-resident camera hardware to point at.
export default function MemberCameraScreen({ route, navigation }: Props) {
  const { memberName } = route.params;
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);

  if (!user) return null;

  const url = videoFeedUrl(user.token);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>{memberName}&apos;s Camera</Text>
          <Text style={styles.subtitle}>Simulated -- shared demo feed</Text>
        </View>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={styles.closeButton}>Close</Text>
        </TouchableOpacity>
      </View>

      <WebView source={{ html: buildHtml(url) }} onLoadEnd={() => setLoading(false)} style={styles.webview} />
      {loading && (
        <View style={styles.overlay}>
          <ActivityIndicator size="large" color="#fff" />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000" },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 16,
    paddingTop: 50,
    backgroundColor: "#0f172a",
  },
  title: { color: "#fff", fontSize: 18, fontWeight: "700" },
  subtitle: { color: "#64748b", fontSize: 11, marginTop: 2 },
  closeButton: { color: "#60a5fa", fontSize: 16, fontWeight: "600" },
  webview: { flex: 1, backgroundColor: "#000" },
  overlay: { ...StyleSheet.absoluteFill, justifyContent: "center", alignItems: "center", backgroundColor: "#000" },
});
