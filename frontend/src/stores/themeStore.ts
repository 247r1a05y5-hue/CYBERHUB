import { create } from "zustand";

type Theme = "dark";

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

/** Apply pure-black theme tokens to root HTML element */
function applyTheme(theme: Theme = "dark") {
  document.documentElement.setAttribute("data-theme", "dark");
  document.documentElement.classList.add("dark");
}

export const useThemeStore = create<ThemeState>((set) => ({
  theme: "dark",
  setTheme: (_theme) => {
    localStorage.setItem("cyberhub_theme", "dark");
    applyTheme("dark");
    set({ theme: "dark" });
  },
  toggleTheme: () => {
    applyTheme("dark");
  },
}));
