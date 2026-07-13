export type Role = "Admin" | "Operator";

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
