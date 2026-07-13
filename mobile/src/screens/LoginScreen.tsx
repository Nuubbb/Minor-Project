import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";
import { Role } from "../types";
import type { AuthStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<AuthStackParamList, "Login">;

export default function LoginScreen({ navigation }: Props) {
  const { login } = useAuth();
  const [role, setRole] = useState<Role>("Operator");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async () => {
    setError(null);
    if (!username || !password) {
      setError("Enter username/email and password.");
      return;
    }
    setLoading(true);
    try {
      await login(role, username, password);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not reach the server.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <Text style={styles.title}>Surveillance System</Text>
      <Text style={styles.subtitle}>Sign in to your account</Text>

      <View style={styles.roleRow}>
        {(["Operator", "Admin"] as Role[]).map((r) => (
          <TouchableOpacity
            key={r}
            style={[styles.roleButton, role === r && styles.roleButtonActive]}
            onPress={() => setRole(r)}
          >
            <Text style={[styles.roleButtonText, role === r && styles.roleButtonTextActive]}>{r}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <TextInput
        style={styles.input}
        placeholder="Username or email"
        autoCapitalize="none"
        value={username}
        onChangeText={setUsername}
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />

      {error && <Text style={styles.error}>{error}</Text>}

      <TouchableOpacity style={styles.submitButton} onPress={onSubmit} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.submitButtonText}>Log In</Text>}
      </TouchableOpacity>

      <TouchableOpacity onPress={() => navigation.navigate("Signup")}>
        <Text style={styles.link}>Need an operator account? Sign up</Text>
      </TouchableOpacity>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: 24, backgroundColor: "#0f172a" },
  title: { fontSize: 26, fontWeight: "700", color: "#fff", textAlign: "center" },
  subtitle: { fontSize: 14, color: "#94a3b8", textAlign: "center", marginBottom: 24 },
  roleRow: { flexDirection: "row", marginBottom: 16, backgroundColor: "#1e293b", borderRadius: 8, padding: 4 },
  roleButton: { flex: 1, paddingVertical: 10, borderRadius: 6, alignItems: "center" },
  roleButtonActive: { backgroundColor: "#2563eb" },
  roleButtonText: { color: "#94a3b8", fontWeight: "600" },
  roleButtonTextActive: { color: "#fff" },
  input: {
    backgroundColor: "#1e293b",
    color: "#fff",
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 12,
  },
  error: { color: "#f87171", marginBottom: 12, textAlign: "center" },
  submitButton: { backgroundColor: "#2563eb", borderRadius: 8, paddingVertical: 14, alignItems: "center" },
  submitButtonText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  link: { color: "#60a5fa", textAlign: "center", marginTop: 16 },
});
