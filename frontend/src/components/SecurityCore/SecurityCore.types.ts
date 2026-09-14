export type SecurityCoreState =
  | "idle"
  | "observing"
  | "analyzing"
  | "high-risk"
  | "investigating"
  | "secure";

export type SecurityCoreSize = "hero" | "section" | "nav" | "inline";

export interface SecurityCoreProps {
  state: SecurityCoreState;
  size?: SecurityCoreSize;
  interactive?: boolean;
  className?: string;
  onStateSettled?: () => void;
}
