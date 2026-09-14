import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Image, FolderOpen, FileText, Shield, LayoutDashboard } from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";

interface CommandAction {
  id: string;
  label: string;
  href: string;
  icon: React.ElementType;
  group: string;
  keywords?: string[];
}

const COMMANDS: CommandAction[] = [
  { id: "dashboard",      label: "Dashboard",           href: "/dashboard",                     icon: LayoutDashboard, group: "Navigation" },
  { id: "image-exposure", label: "Image Exposure",      href: "/investigations/image-exposure",  icon: Image,           group: "Investigations", keywords: ["lens", "reverse", "camera", "scan"] },
  { id: "evidence",       label: "Evidence Vault",      href: "/evidence",                       icon: FolderOpen,      group: "Navigation" },
  { id: "reports",        label: "Reports",             href: "/reports",                        icon: FileText,        group: "Navigation" },
  { id: "security",       label: "Security Center",     href: "/security",                       icon: Shield,          group: "Platform" },
];

export const CommandBar: React.FC = () => {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      setOpen((v) => !v);
    }
  }, []);

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const handleSelect = (href: string) => {
    setOpen(false);
    navigate(href);
  };

  const groups = Array.from(new Set(COMMANDS.map((c) => c.group)));

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Navigate to... (type a command)" />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        {groups.map((group, gi) => (
          <React.Fragment key={group}>
            {gi > 0 && <CommandSeparator />}
            <CommandGroup heading={group}>
              {COMMANDS.filter((c) => c.group === group).map((cmd) => {
                const Icon = cmd.icon;
                return (
                  <CommandItem
                    key={cmd.id}
                    value={[cmd.label, ...(cmd.keywords ?? [])].join(" ")}
                    onSelect={() => handleSelect(cmd.href)}
                  >
                    <Icon className="mr-2 h-4 w-4" aria-hidden="true" />
                    {cmd.label}
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </React.Fragment>
        ))}
      </CommandList>
    </CommandDialog>
  );
};
