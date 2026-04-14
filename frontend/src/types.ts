export type MessageType = "user" | "agent" | "system";

export interface Message {
  type: MessageType;
  text: string | object;
}