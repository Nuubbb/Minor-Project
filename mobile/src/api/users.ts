import { api } from "./client";
import { UserItem } from "../types";

export function getUsers(): Promise<UserItem[]> {
  return api.get<{ users: UserItem[] }>(`/api/users`).then((res) => res.users);
}

export function deleteUser(userId: number): Promise<void> {
  return api.delete(`/api/users/${userId}`).then(() => undefined);
}
