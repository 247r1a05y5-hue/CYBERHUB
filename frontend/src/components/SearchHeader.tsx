import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Search, User, ShieldCheck, Sparkles, Image, Plus } from "lucide-react";
import { useAuthStore } from "../stores/authStore";

interface SearchHeaderProps {
  onNewSearch?: () => void;
}

export const SearchHeader: React.FC<SearchHeaderProps> = ({ onNewSearch }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const handleNewSearchClick = () => {
    if (onNewSearch) {
      onNewSearch();
    } else {
      navigate("/dashboard");
    }
  };

  return (
    <header className="h-16 bg-white border-b border-gray-200 px-4 sm:px-8 flex items-center justify-between sticky top-0 z-40 shadow-xs">
      {/* Left: Brand Logo & Navigation */}
      <div className="flex items-center gap-8">
        <Link
          to="/dashboard"
          className="flex items-center gap-2 text-gray-900 font-bold text-lg tracking-tight hover:opacity-90 transition"
        >
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-sm font-mono font-bold text-sm">
            C
          </div>
          <span className="font-extrabold text-base tracking-tight text-gray-900">
            cyberhub<span className="text-indigo-600">.ai</span>
          </span>
        </Link>

        {/* Navigation Tabs */}
        <nav className="hidden md:flex items-center gap-6 text-xs font-semibold text-gray-600">
          <Link
            to="/dashboard"
            className={`pb-0.5 border-b-2 transition-colors ${
              location.pathname === "/dashboard" || location.pathname === "/"
                ? "text-gray-900 border-indigo-600"
                : "border-transparent hover:text-gray-900"
            }`}
          >
            Reverse Image Search
          </Link>
          <Link
            to="/dashboard?mode=face"
            className="border-b-2 border-transparent hover:text-gray-900 transition-colors"
          >
            Face Search
          </Link>
          <Link
            to="/dataset"
            className={`pb-0.5 border-b-2 transition-colors flex items-center gap-1.5 ${
              location.pathname === "/dataset"
                ? "text-gray-900 border-indigo-600"
                : "border-transparent hover:text-gray-900"
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            Controlled Dataset
          </Link>
        </nav>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-3">
        {/* New Search (Dashed button matching reference video) */}
        <button
          type="button"
          onClick={handleNewSearchClick}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border-2 border-dashed border-amber-500/80 bg-amber-50/50 hover:bg-amber-100/60 text-amber-900 font-semibold text-xs transition-all shadow-2xs cursor-pointer"
        >
          <Search className="w-3.5 h-3.5 text-amber-700" />
          <span>New search</span>
        </button>

        {/* Account Button */}
        <button
          type="button"
          onClick={() => navigate("/security")}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#5B50E6] hover:bg-[#4F46E5] text-white font-semibold text-xs transition-all shadow-sm cursor-pointer"
        >
          <User className="w-3.5 h-3.5 text-white" />
          <span>Account</span>
        </button>
      </div>
    </header>
  );
};
