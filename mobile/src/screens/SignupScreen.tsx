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
import type { AuthStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<AuthStackParamList, "Signup">;

export default function SignupScreen({ navigation }: Props) {
  const { signup } = useAuth();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const onSubmit = async () => {
    setError(null);
    if (!username || !password) {
      setError("Username and password are required.");
      return;
    }
    setLoading(true);
    try {
      await signup(username, password, email);
      setSuccess(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not reach the server.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <Text style={styles.title}>Create Operator Account</Text>

      {success ? (
        <>
          <Text style={styles.success}>Account created! You can now log in.</Text>
          <TouchableOpacity style={styles.submitButton} onPress={() => navigation.navigate("Login")}>
            <Text style={styles.submitButtonText}>Go to Login</Text>
          </TouchableOpacity>
        </>
      ) : (
        <>
          <TextInput
            style={styles.input}
            placeholder="Username"
            autoCapitalize="none"
            value={username}
            onChangeText={setUsername}
          />
          <TextInput
            style={styles.input}
            placeholder="Email"
            autoCapitalize="none"
            keyboardType="email-address"
            value={email}
            onChangeText={setEmail}
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
            {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.submitButtonText}>Sign Up</Text>}
          </TouchableOpacity>

          <TouchableOpacity onPress={() => navigation.navigate("Login")}>
            <Text style={styles.link}>Already have an account? Log in</Text>
          </TouchableOpacity>
        </>
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: 24, backgroundColor: "#0f172a" },
  title: { fontSize: 22, fontWeight: "700", color: "#fff", textAlign: "center", marginBottom: 24 },
  input: {
    backgroundColor: "#1e293b",
    color: "#fff",
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 12,
  },
  error: { color: "#f87171", marginBottom: 12, textAlign: "center" },
  success: { color: "#4ade80", marginBottom: 20, textAlign: "center", fontSize: 16 },
  submitButton: { backgroundColor: "#2563eb", borderRadius: 8, paddingVertical: 14, alignItems: "center" },
  submitButtonText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  link: { color: "#60a5fa", textAlign: "center", marginTop: 16 },
});
