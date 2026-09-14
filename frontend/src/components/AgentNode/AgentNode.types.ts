export type AgentNodeState = "idle" | "processing" | "executing" | "completed";

export type AgentNodeAction = "analyze" | "contain" | "respond" | "resolve";

export type AgentNodeSize = "default" | "small";

export interface AgentNodeProps {
  action: AgentNodeAction;
  state: AgentNodeState;
  size?: AgentNodeSize;
  onSettled?: () => void;
  className?: string;
}

export const ACTION_LABELS: Record<AgentNodeAction, string> = {
  analyze: "Analysis agent",
  contain: "Containment agent",
  respond: "Response agent",
  resolve: "Resolution agent",
};
