import { api } from "./client";
import { EventItem } from "../types";

export function getEvents(): Promise<EventItem[]> {
  return api.get<{ events: EventItem[] }>(`/api/events`).then((res) => res.events);
}

export function addEvent(event: {
  event_date: string;
  name: string;
  start_hour: number;
  end_hour: number;
  expected_crowd: number;
}): Promise<void> {
  return api.post(`/api/events`, event).then(() => undefined);
}

export function deleteEvent(eventId: number): Promise<void> {
  return api.delete(`/api/events/${eventId}`).then(() => undefined);
}
