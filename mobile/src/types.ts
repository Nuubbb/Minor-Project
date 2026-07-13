export type Role = "Admin" | "Operator" | "Resident";

export interface AuthUser {
  token: string;
  username: string;
  role: Role;
  email: string | null;
}

export interface Alert {
  id: number;
  timestamp: string;
  alert_type: string;
  confidence: number;
  is_false_alarm: boolean;
  operator_username: string;
}

export interface EventItem {
  id: number;
  event_date: string;
  name: string;
  start_hour: number;
  end_hour: number;
  expected_crowd: number;
}

export interface UserItem {
  id: number;
  username: string;
  email: string | null;
  role: Role;
}

export interface CommunityMember {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  lat: number | null;
  lng: number | null;
}

export interface DeviceLocation {
  label: string;
  lat: number;
  lng: number;
}

export interface MessagePacket {
  id: number;
  alert_type: string;
  confidence: number;
  timestamp: string;
  operator_username: string;
  is_false_alarm: boolean;
  screenshot_url: string | null;
  location: DeviceLocation;
  recipients: CommunityMember[];
}

export interface PeerReport {
  id: number;
  reporter_user_id: number;
  reporter_username: string;
  owner_user_id: number;
  message: string | null;
  status: "pending" | "confirmed" | "dismissed";
  timestamp: string;
}
