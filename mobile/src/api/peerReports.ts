import { api } from "./client";
import { PeerReport } from "../types";

export function createPeerReport(ownerUserId: number, message?: string): Promise<{ id: number }> {
  return api.post(`/api/peer_reports`, { owner_user_id: ownerUserId, message });
}

export function getPendingReportsForMe(): Promise<PeerReport[]> {
  return api.get<{ peer_reports: PeerReport[] }>(`/api/peer_reports?for_me=true`).then((res) => res.peer_reports);
}

export function validatePeerReport(reportId: number, confirmed: boolean): Promise<{ message: string }> {
  return api.post(`/api/peer_reports/${reportId}/validate`, { confirmed });
}
