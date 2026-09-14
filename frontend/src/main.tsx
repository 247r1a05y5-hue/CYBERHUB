import React, { useEffect } from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "./app/router";
import { useThemeStore } from "./stores/themeStore";
import { useAuthStore } from "./stores/authStore";
import "./index.css";

const RootApp: React.FC = () => {
  const { theme } = useThemeStore();
  const { initialize } = useAuthStore();

  useEffect(() => {
    // Sync both data-theme (CyberHub custom tokens) and .dark class (shadcn components)
    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.classList.toggle("dark", theme === "dark");
    initialize();
  }, [theme, initialize]);

  return <RouterProvider router={router} />;
};

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RootApp />
  </React.StrictMode>
);

