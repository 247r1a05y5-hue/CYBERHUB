import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  componentName?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(
      `[ErrorBoundary${this.props.componentName ? `: ${this.props.componentName}` : ""}] Caught rendering error:`,
      error,
      errorInfo
    );
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="p-6 my-4 rounded-xl bg-[#0C0C0C] border border-[#ef4444]/40 text-left space-y-4 shadow-lg">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-[#ef4444] shrink-0 mt-0.5" />
            <div className="space-y-1 flex-1">
              <h4 className="text-sm font-semibold text-[#F5F5F5]">
                {this.props.componentName ? `${this.props.componentName} Render Error` : "Component Render Error"}
              </h4>
              <p className="text-xs text-[#B3B3B3] font-mono leading-relaxed">
                {this.state.error?.message || "An unexpected rendering error occurred inside this component."}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={this.handleReset}
            className="px-3.5 py-1.5 bg-[#151515] hover:bg-[#1E1E1E] text-[#F5F5F5] border border-[#2B2B2B] text-xs font-semibold rounded flex items-center gap-2 transition-colors active:scale-95"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reset View</span>
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
