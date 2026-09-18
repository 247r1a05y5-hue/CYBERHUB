import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Image,
  Shield,
  Clock,
  Bookmark,
  CheckCircle2,
  Lock,
  FileText,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  X,
  Layers,
} from "lucide-react";
import { useAuthStore } from "../../stores/authStore";

interface AppSidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

export const AppSidebar: React.FC<AppSidebarProps> = ({
  isCollapsed,
  onToggleCollapse,
  isMobileOpen,
  onCloseMobile,
}) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const isRouteActive = (path: string) => {
    if (path === "/dashboard" && (location.pathname === "/dashboard" || location.pathname === "/investigations/image-exposure")) {
      return true;
    }
    return location.pathname === path;
  };

  const navGroups = [
    {
      title: "INVESTIGATE",
      items: [
        {
          label: "Image Search",
          path: "/dashboard",
          icon: Image,
          active: isRouteActive("/dashboard"),
        },
        {
          label: "Dataset Match",
          path: "/dataset",
          icon: Shield,
          active: isRouteActive("/dataset"),
        },
      ],
    },
    {
      title: "SEARCHES",
      items: [
        {
          label: "Recent Investigations",
          path: "/searches/recent",
          icon: Clock,
          active: isRouteActive("/searches/recent"),
        },
        {
          label: "Saved Searches",
          path: "/searches/saved",
          icon: Bookmark,
          active: isRouteActive("/searches/saved"),
        },
      ],
    },
    {
      title: "RESULTS",
      items: [
        {
          label: "Matches",
          path: "/results/matches",
          icon: Layers,
          active: isRouteActive("/results/matches"),
        },
        {
          label: "Verified Findings",
          path: "/results/verified",
          icon: CheckCircle2,
          active: isRouteActive("/results/verified"),
        },
        {
          label: "Evidence",
          path: "/evidence",
          icon: Lock,
          active: isRouteActive("/evidence"),
        },
      ],
    },
    {
      title: "TOOLS",
      items: [
        {
          label: "Reports",
          path: "/reports",
          icon: FileText,
          active: isRouteActive("/reports"),
        },
        {
          label: "Settings",
          path: "/security",
          icon: Settings,
          active: isRouteActive("/security"),
        },
      ],
    },
  ];

  const userInitials = user?.email
    ? user.email.substring(0, 2).toUpperCase()
    : "AN";

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/80 backdrop-blur-sm lg:hidden transition-opacity"
          onClick={onCloseMobile}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 flex flex-col bg-[#050505] border-r border-[#1A1A1A] transition-all duration-200 ease-in-out ${
          isCollapsed ? "w-16" : "w-60"
        } ${
          isMobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        {/* Header / Brand */}
        <div className="h-14 px-4 flex items-center justify-between border-b border-[#1A1A1A] shrink-0 bg-[#050505]">
          <Link
            to="/dashboard"
            onClick={onCloseMobile}
            className="flex items-center gap-2.5 text-[#F5F5F5] hover:opacity-90 transition-opacity focus:outline-none overflow-hidden"
          >
            <div className="w-6 h-6 rounded-md bg-[#111111] border border-[#2B2B2B] flex items-center justify-center font-mono font-bold text-xs text-[#F5F5F5] shrink-0">
              C
            </div>
            {!isCollapsed && (
              <span className="font-bold text-xs tracking-[0.18em] uppercase select-none text-[#F5F5F5] truncate">
                CYBERHUB
              </span>
            )}
          </Link>

          {/* Mobile close button */}
          <button
            type="button"
            onClick={onCloseMobile}
            className="p-1 rounded-md text-[#777777] hover:text-[#F5F5F5] hover:bg-[#111111] lg:hidden"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation Sections */}
        <div className="flex-1 overflow-y-auto py-3 px-2 space-y-5">
          {navGroups.map((group) => (
            <div key={group.title} className="space-y-1">
              {!isCollapsed && (
                <p className="px-3 text-[10px] font-bold text-[#777777] tracking-[0.14em] uppercase mb-1.5 select-none">
                  {group.title}
                </p>
              )}

              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={onCloseMobile}
                    title={isCollapsed ? item.label : undefined}
                    className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                      item.active
                        ? "bg-[#1A1A1A] text-[#F5F5F5] border border-[#2B2B2B]"
                        : "text-[#B3B3B3] hover:text-[#F5F5F5] hover:bg-[#0C0C0C] border border-transparent"
                    } ${isCollapsed ? "justify-center px-0" : ""}`}
                  >
                    <Icon className={`w-4 h-4 shrink-0 ${item.active ? "text-[#F5F5F5]" : "text-[#777777]"}`} />
                    {!isCollapsed && <span className="truncate">{item.label}</span>}
                  </Link>
                );
              })}
            </div>
          ))}
        </div>

        {/* User / Bottom Footer */}
        <div className="p-2 border-t border-[#1A1A1A] shrink-0 space-y-1 bg-[#050505]">
          {/* User profile tile */}
          <div
            className={`flex items-center gap-2.5 px-2.5 py-2 rounded-lg bg-[#0C0C0C] border border-[#1A1A1A] ${
              isCollapsed ? "justify-center p-2" : ""
            }`}
          >
            <div className="w-6 h-6 rounded-full bg-[#151515] border border-[#2B2B2B] text-[#F5F5F5] font-mono text-[10px] flex items-center justify-center shrink-0">
              {userInitials}
            </div>

            {!isCollapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-[#F5F5F5] truncate">
                  {user?.email || "analyst@cyberhub.local"}
                </p>
                <p className="text-[10px] text-[#777777] truncate flex items-center gap-1">
                  <Shield className="w-2.5 h-2.5 text-[#777777]" />
                  <span>Security Analyst</span>
                </p>
              </div>
            )}
          </div>

          {/* Logout button */}
          <button
            type="button"
            onClick={handleLogout}
            title={isCollapsed ? "Logout" : undefined}
            className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-xs text-[#777777] hover:text-[#ef4444] hover:bg-[#111111] transition-colors ${
              isCollapsed ? "justify-center px-0" : ""
            }`}
          >
            <LogOut className="w-3.5 h-3.5 shrink-0" />
            {!isCollapsed && <span>Logout</span>}
          </button>

          {/* Desktop collapse toggle */}
          <div className="hidden lg:flex justify-end pt-1">
            <button
              type="button"
              onClick={onToggleCollapse}
              className="p-1 rounded-md text-[#777777] hover:text-[#F5F5F5] hover:bg-[#111111] transition-colors"
              title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {isCollapsed ? (
                <ChevronRight className="w-3.5 h-3.5" />
              ) : (
                <ChevronLeft className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};
