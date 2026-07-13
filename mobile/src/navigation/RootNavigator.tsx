import React from "react";
import { View, ActivityIndicator, StyleSheet } from "react-native";
import { NavigationContainer, DarkTheme } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { useAuth } from "../context/AuthContext";
import LoginScreen from "../screens/LoginScreen";
import SignupScreen from "../screens/SignupScreen";
import AlertValidatorScreen from "../screens/AlertValidatorScreen";
import PeerReportValidatorScreen from "../screens/PeerReportValidatorScreen";
import MemberCameraScreen from "../screens/MemberCameraScreen";
import MainTabs from "./MainTabs";
import { navigationRef } from "./navigationRef";
import type { AuthStackParamList, RootStackParamList } from "./types";

const AuthStack = createNativeStackNavigator<AuthStackParamList>();
const RootStack = createNativeStackNavigator<RootStackParamList>();

function AuthNavigator() {
  return (
    <AuthStack.Navigator screenOptions={{ headerShown: false }}>
      <AuthStack.Screen name="Login" component={LoginScreen} />
      <AuthStack.Screen name="Signup" component={SignupScreen} />
    </AuthStack.Navigator>
  );
}

function LoggedInNavigator() {
  return (
    <RootStack.Navigator screenOptions={{ headerShown: false }}>
      <RootStack.Screen name="Tabs" component={MainTabs} />
      <RootStack.Screen name="AlertValidator" component={AlertValidatorScreen} options={{ presentation: "modal" }} />
      <RootStack.Screen name="PeerReportValidator" component={PeerReportValidatorScreen} options={{ presentation: "modal" }} />
      <RootStack.Screen name="MemberCamera" component={MemberCameraScreen} options={{ presentation: "modal" }} />
    </RootStack.Navigator>
  );
}

export default function RootNavigator() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" color="#fff" />
      </View>
    );
  }

  return (
    <NavigationContainer ref={navigationRef} theme={DarkTheme}>
      {user ? <LoggedInNavigator /> : <AuthNavigator />}
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  loading: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#0f172a" },
});
