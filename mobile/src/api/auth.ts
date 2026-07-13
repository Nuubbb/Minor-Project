import { api } from "./client";
import { AuthUser, Role } from "../types";

interface LoginResponse {
  token: string;
  username: string;
  role: Role;
  email: string | null;
}

export function login(roleType: Role, username: string, password: string): Promise<AuthUser> {
  return api
    .post<LoginResponse>(`/api/login/${roleType.toLowerCase()}`, { username, password }, { skipAuth: true })
    .then((res) => ({ token: res.token, username: res.username, role: res.role, email: res.email }));
}

export function signup(username: string, password: string, email: string): Promise<void> {
  return api.post(`/api/signup`, { username, password, email }, { skipAuth: true }).then(() => undefined);
}

export function me(): Promise<{ username: string; role: Role; email: string | null }> {
  return api.get(`/api/me`);
}
