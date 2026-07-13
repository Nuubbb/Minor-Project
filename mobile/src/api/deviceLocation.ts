import { api } from "./client";
import { DeviceLocation } from "../types";

export function getDeviceLocation(): Promise<DeviceLocation> {
  return api.get<DeviceLocation>(`/api/device_location`);
}

export function updateDeviceLocation(label: string, lat: number, lng: number): Promise<DeviceLocation> {
  return api.put<DeviceLocation>(`/api/device_location`, { label, lat, lng });
}
