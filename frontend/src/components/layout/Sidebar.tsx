import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Image,
  FolderOpen,
  FileText,
  Shield,
  ChevronLeft,
  ChevronRight,
  Menu,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Separator } from "@/components/ui/separator";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard",       href: "/dashboard",                    icon: LayoutDashboard },
  { label: "Image Exposure",  href: "/investigations/image-exposure", icon: Image },
  { label: "Evidence Vault",  href: "/evidence",                     icon: FolderOpen },
  { label: "Reports",         href: "/reports",                      icon: FileText },
];

const SECONDARY_NAV: NavItem[] = [
  { label: "Security Center", href: "/security", icon: Shield },
];

interface SidebarNavProps {
  collapsed?: boolean;
  onClose?: () => void;
}

const SidebarNav: React.FC<SidebarNavProps> = ({ collapsed = false, onClose }) => {
  const location = useLocation();

  const NavLink = ({ item }: { item: NavItem }) => {
    const Icon = item.icon;
    const isActive = location.pathname === item.href ||
      (item.href !== "/dashboard" && location.pathname.startsWith(item.href));

    return (
      <Link
        to={item.href}
        onClick={onClose}
        className={cn(
          "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          isActive
            ? "bg-primary/10 text-primary"
            : "text-muted-foreground hover:text-foreground hover:bg-accent"
        )}
        aria-current={isActive ? "page" : undefined}
      >
        <Icon className={cn("shrink-0", collapsed ? "w-5 h-5" : "w-4 h-4")} aria-hidden="true" />
        {!collapsed && <span className="truncate">{item.label}</span>}
        {!collapsed && item.badge && (
          <span className="ml-auto text-[10px] font-semibold bg-primary/15 text-primary px-1.5 py-0.5 rounded-full">
            {item.badge}
          </span>
        )}
      </Link>
    );
  };

  return (
    <nav className="flex flex-col h-full py-4 gap-1" aria-label="Main navigation">
      <div className="px-3 mb-1">
        {!collapsed && (
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground px-0 mb-1">
            Investigations
          </p>
        )}
        {NAV_ITEMS.map((item) => (
          <NavLink key={item.href} item={item} />
        ))}
      </div>

      <Separator className="my-2 mx-3 w-auto" />

      <div className="px-3">
        {!collapsed && (
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground px-0 mb-1">
            Platform
          </p>
        )}
        {SECONDARY_NAV.map((item) => (
          <NavLink key={item.href} item={item} />
        ))}
      </div>
    </nav>
  );
};

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ collapsed, onToggleCollapse }) => {
  return (
    <aside
      className={cn(
        "hidden md:flex flex-col border-r border-border bg-card transition-all duration-200 shrink-0 relative",
        collapsed ? "w-14" : "w-56"
      )}
    >
      <SidebarNav collapsed={collapsed} />

      <button
        type="button"
        onClick={onToggleCollapse}
        className={cn(
          "absolute -right-3 top-6 z-10 w-6 h-6 rounded-full border border-border bg-background",
          "flex items-center justify-center text-muted-foreground hover:text-foreground",
          "transition-colors shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        )}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
      </button>
    </aside>
  );
};

export const MobileSidebar: React.FC = () => {
  const [open, setOpen] = useState(false);
  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-56 p-0 pt-12">
        <SidebarNav onClose={() => setOpen(false)} />
      </SheetContent>
    </Sheet>
  );
};
