import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../context/AuthContext";
import DashboardScreen from "../screens/DashboardScreen";
import LiveCameraScreen from "../screens/LiveCameraScreen";
import AlertHistoryScreen from "../screens/AlertHistoryScreen";
import CommunityScreen from "../screens/CommunityScreen";
import CommunityMapScreen from "../screens/CommunityMapScreen";
import EventsScreen from "../screens/EventsScreen";
import UsersScreen from "../screens/UsersScreen";
import ProfileScreen from "../screens/ProfileScreen";
import { AlertBadgeProvider, useAlertBadge } from "../context/AlertBadgeContext";
import { useAlertNotifications } from "../notifications/useAlertNotifications";
import { usePeerReportNotifications } from "../notifications/usePeerReportNotifications";
import type { MainTabParamList } from "./types";

const Tab = createBottomTabNavigator<MainTabParamList>();

type IoniconName = keyof typeof Ionicons.glyphMap;

const TAB_ICONS: Record<keyof MainTabParamList, IoniconName> = {
  Dashboard: "grid-outline",
  Live: "videocam-outline",
  History: "time-outline",
  Community: "megaphone-outline",
  Map: "map-outline",
  Events: "calendar-outline",
  Users: "people-outline",
  Profile: "person-outline",
};

function tabBarIcon(name: keyof MainTabParamList) {
  return ({ color, size }: { color: string; size: number }) => (
    <Ionicons name={TAB_ICONS[name]} color={color} size={size} />
  );
}

export default function MainTabs() {
  return (
    <AlertBadgeProvider>
      <MainTabsInner />
    </AlertBadgeProvider>
  );
}

function MainTabsInner() {
  const { user } = useAuth();
  const { unseenCount } = useAlertBadge();
  const isAdmin = user?.role === "Admin";
  useAlertNotifications();
  usePeerReportNotifications();

  return (
    <Tab.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: "#0f172a" },
        headerTintColor: "#fff",
        tabBarStyle: { backgroundColor: "#0f172a", borderTopColor: "#1e293b" },
        tabBarActiveTintColor: "#60a5fa",
        tabBarInactiveTintColor: "#64748b",
      }}
    >
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{
          title: "Dashboard",
          tabBarIcon: tabBarIcon("Dashboard"),
          tabBarBadge: unseenCount > 0 ? unseenCount : undefined,
        }}
      />
      <Tab.Screen
        name="Live"
        component={LiveCameraScreen}
        options={{ title: "Live Camera", tabBarIcon: tabBarIcon("Live") }}
      />
      <Tab.Screen
        name="History"
        component={AlertHistoryScreen}
        options={{ title: "History", tabBarIcon: tabBarIcon("History") }}
      />
      <Tab.Screen
        name="Community"
        component={CommunityScreen}
        options={{ title: "Community", tabBarIcon: tabBarIcon("Community") }}
      />
      <Tab.Screen
        name="Map"
        component={CommunityMapScreen}
        options={{ title: "Map", tabBarIcon: tabBarIcon("Map") }}
      />
      {isAdmin && (
        <Tab.Screen
          name="Events"
          component={EventsScreen}
          options={{ title: "Events", tabBarIcon: tabBarIcon("Events") }}
        />
      )}
      {isAdmin && (
        <Tab.Screen
          name="Users"
          component={UsersScreen}
          options={{ title: "Users", tabBarIcon: tabBarIcon("Users") }}
        />
      )}
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{ title: "Profile", tabBarIcon: tabBarIcon("Profile") }}
      />
    </Tab.Navigator>
  );
}
