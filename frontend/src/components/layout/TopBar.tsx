import React from "react";
import { useNavigate } from "react-router-dom";
import { Sun, Moon, Search, LogOut, User, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { Breadcrumbs } from "./Breadcrumbs";
import { MobileSidebar } from "./Sidebar";
import { useThemeStore } from "@/stores/themeStore";
import { useAuthStore } from "@/stores/authStore";
import { cn } from "@/lib/utils";

interface TopBarProps {
  onOpenCommandBar?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({ onOpenCommandBar }) => {
  const { theme, toggleTheme } = useThemeStore();
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const initials = user?.email
    ? user.email[0].toUpperCase()
    : "U";

  return (
    <TooltipProvider delayDuration={400}>
      <header className="sticky top-0 z-40 flex h-14 items-center gap-3 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 px-4">
        {/* Mobile menu */}
        <MobileSidebar />

        {/* Brand */}
        <div className="flex items-center gap-2 font-semibold text-foreground select-none">
          <div className="w-7 h-7 rounded bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold tracking-tight shrink-0">
            CH
          </div>
          <span className="hidden sm:inline text-sm tracking-wide">CyberHub</span>
        </div>

        <Separator orientation="vertical" className="h-5 hidden sm:block" />

        {/* Breadcrumbs */}
        <div className="flex-1 min-w-0 hidden sm:block">
          <Breadcrumbs />
        </div>

        {/* Right controls */}
        <div className="flex items-center gap-1 ml-auto">
          {/* Search / command bar trigger */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={onOpenCommandBar}
                className="hidden md:flex items-center gap-2 text-muted-foreground hover:text-foreground h-8 px-3"
                aria-label="Open command bar (Ctrl+K)"
              >
                <Search className="h-3.5 w-3.5" aria-hidden="true" />
                <span className="text-xs hidden lg:inline">Search</span>
                <kbd className="hidden lg:inline-flex items-center gap-0.5 rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
                  <span>⌘</span><span>K</span>
                </kbd>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom">Command palette (Ctrl+K)</TooltipContent>
          </Tooltip>

          {/* Theme toggle */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleTheme}
                className="h-8 w-8"
                aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
              >
                {theme === "dark" ? (
                  <Sun className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <Moon className="h-4 w-4" aria-hidden="true" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              {theme === "dark" ? "Light mode" : "Dark mode"}
            </TooltipContent>
          </Tooltip>

          {/* User menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="h-8 w-8 rounded-full p-0"
                aria-label="User menu"
              >
                <Avatar className="h-7 w-7">
                  <AvatarFallback className="text-xs bg-primary/10 text-primary font-semibold">
                    {initials}
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52">
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-0.5">
                  {user?.email && (
                    <p className="text-sm font-medium leading-none">{user.email}</p>
                  )}
                  {user?.role && (
                    <p className="text-xs leading-none text-muted-foreground mt-0.5">{user.role}</p>
                  )}
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="gap-2 text-sm cursor-pointer">
                <User className="h-3.5 w-3.5" aria-hidden="true" />
                Profile
              </DropdownMenuItem>
              <DropdownMenuItem className="gap-2 text-sm cursor-pointer">
                <Settings className="h-3.5 w-3.5" aria-hidden="true" />
                Settings
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="gap-2 text-sm text-destructive cursor-pointer focus:text-destructive"
                onClick={handleLogout}
              >
                <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>
    </TooltipProvider>
  );
};
