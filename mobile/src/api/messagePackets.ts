import { api } from "./client";
import { MessagePacket, CommunityMember } from "../types";

export function getMessagePackets(limit?: number): Promise<MessagePacket[]> {
  const query = limit ? `?limit=${limit}` : "";
  return api.get<{ message_packets: MessagePacket[] }>(`/api/message_packets${query}`).then((res) => res.message_packets);
}

export function sendMessagePacket(alertId: number): Promise<{ sent: number; failed: number }> {
  return api.post(`/api/message_packets/${alertId}/send`);
}

export function getCommunity(): Promise<CommunityMember[]> {
  return api.get<{ community: CommunityMember[] }>(`/api/community`).then((res) => res.community);
}
