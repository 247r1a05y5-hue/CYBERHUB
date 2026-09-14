import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Bell,
  Menu,
  LogOut,
  User as UserIcon,
  Shield,
  Activity,
  Check,
} from "lucide-react";
import { useAuthStore } from "../../stores/authStore";

interface AppHeaderProps {
  onToggleSidebar?: () => void;
  onSearch?: (query: string) => void;
}

export const AppHeader: React.FC<AppHeaderProps> = ({
  onToggleSidebar,
  onSearch,
}) => {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [searchQuery, setSearchQuery] = useState("");
  const [showUserMenu, setShowUserMenu] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSearch) {
      onSearch(searchQuery);
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const userInitials = user?.email
    ? user.email.substring(0, 2).toUpperCase()
    : "AN";

  return (
    <header className="h-14 bg-[#000000] border-b border-[#1A1A1A] sticky top-0 z-30 flex items-center justify-between px-4 sm:px-6">
      {/* Left: Sidebar Toggle + Context */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="p-1.5 rounded-md text-[#777777] hover:text-[#F5F5F5] hover:bg-[#111111] transition-colors focus:outline-none"
          title="Toggle Navigation"
        >
          <Menu className="w-4 h-4" />
        </button>

        <div className="hidden sm:flex items-center gap-2 text-xs text-[#777777]">
          <span>CyberHub</span>
          <span>/</span>
          <span className="text-[#F5F5F5] font-medium">Forensic Workstation</span>
        </div>
      </div>

      {/* Center: Command Palette / Global Search */}
      <div className="flex-1 max-w-md mx-4 hidden md:block">
        <form onSubmit={handleSearchSubmit} className="relative w-full">
          <Search className="w-3.5 h-3.5 text-[#777777] absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search public exposure or jump to case... (⌘K)"
            className="w-full h-8 pl-8 pr-3 text-xs bg-[#0C0C0C] border border-[#1A1A1A] rounded-md text-[#F5F5F5] placeholder-[#777777] focus:outline-none focus:border-[#2B2B2B] transition-colors font-sans"
          />
        </form>
      </div>

      {/* Right: Status Indicator + Notifications + User Menu */}
      <div className="flex items-center gap-3">
        {/* System Status Indicator (Restrained Green Dot) */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#0C0C0C] border border-[#1A1A1A] text-[11px] font-mono text-[#B3B3B3]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />
          <span>SYSTEM READY</span>
        </div>

        {/* Notifications */}
        <button
          type="button"
          className="p-1.5 text-[#777777] hover:text-[#F5F5F5] hover:bg-[#111111] rounded-md transition-colors"
          title="Notifications"
        >
          <Bell className="w-4 h-4" />
        </button>

        {/* User Profile Avatar / Menu */}
        <div className="relative" ref={userMenuRef}>
          <button
            type="button"
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="w-7 h-7 rounded-md bg-[#151515] border border-[#2B2B2B] text-[#F5F5F5] font-mono font-medium text-[11px] flex items-center justify-center hover:bg-[#1A1A1A] transition-colors focus:outline-none"
            title="User menu"
          >
            {userInitials}
          </button>

          {showUserMenu && (
            <div className="absolute right-0 mt-1.5 w-52 bg-[#0C0C0C] border border-[#1A1A1A] rounded-lg shadow-xl py-1.5 z-50 text-xs">
              <div className="px-3 py-2 border-b border-[#1A1A1A]">
                <p className="font-semibold text-[#F5F5F5] truncate">
                  {user?.email || "analyst@cyber.local"}
                </p>
                <p className="text-[11px] text-[#777777] flex items-center gap-1 mt-0.5 font-mono">
                  <Shield className="w-3 h-3 text-[#10B981]" />
                  <span>Security Analyst</span>
                </p>
              </div>

              <div className="py-1">
                <button
                  type="button"
                  onClick={() => {
                    setShowUserMenu(false);
                    navigate("/dashboard");
                  }}
                  className="w-full px-3 py-1.5 text-left text-[#B3B3B3] hover:text-[#F5F5F5] hover:bg-[#151515] flex items-center gap-2 transition-colors"
                >
                  <UserIcon className="w-3.5 h-3.5 text-[#777777]" />
                  <span>Command Center</span>
                </button>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full px-3 py-1.5 text-left text-[#ef4444] hover:bg-[#151515] flex items-center gap-2 font-medium transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Logout</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
