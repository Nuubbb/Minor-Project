import React, { useRef, useState } from "react";
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity } from "react-native";
import { WebView } from "react-native-webview";
import { useAuth } from "../context/AuthContext";
import { videoFeedUrl } from "../api/client";

// MJPEG (multipart/x-mixed-replace) doesn't render reliably when a WebView
// navigates to it directly on iOS. Wrapping it in a plain <img> tag inside a
// tiny HTML document -- the same trick the web dashboard uses -- is the
// reliable cross-platform way to display the stream.
function buildHtml(url: string) {
  return `<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
  <style>html,body{margin:0;padding:0;background:#000;height:100%;}
  img{width:100%;height:100%;object-fit:contain;}</style></head>
  <body><img src="${url}" /></body></html>`;
}

export default function LiveCameraScreen() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);
  const webviewRef = useRef<WebView>(null);

  if (!user) return null;

  const url = videoFeedUrl(user.token);

  return (
    <View style={styles.container}>
      <WebView
        key={reloadKey}
        ref={webviewRef}
        source={{ html: buildHtml(url) }}
        onLoadEnd={() => setLoading(false)}
        style={styles.webview}
      />
      {loading && (
        <View style={styles.overlay}>
          <ActivityIndicator size="large" color="#fff" />
          <Text style={styles.overlayText}>Connecting to camera…</Text>
        </View>
      )}
      <TouchableOpacity
        style={styles.reloadButton}
        onPress={() => {
          setLoading(true);
          setReloadKey((k) => k + 1);
        }}
      >
        <Text style={styles.reloadButtonText}>Reload</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000" },
  webview: { flex: 1, backgroundColor: "#000" },
  overlay: {
    ...StyleSheet.absoluteFill,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#000",
  },
  overlayText: { color: "#94a3b8", marginTop: 12 },
  reloadButton: {
    position: "absolute",
    bottom: 24,
    alignSelf: "center",
    backgroundColor: "rgba(30,41,59,0.9)",
    paddingHorizontal: 18,
    paddingVertical: 10,
    borderRadius: 20,
  },
  reloadButtonText: { color: "#fff", fontWeight: "600" },
});
