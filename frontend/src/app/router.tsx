import React from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { Landing } from "../pages/Landing";
import { Login } from "../pages/Login";
import { CommandCenter } from "../pages/CommandCenter";
import { ImageExposurePage } from "../pages/ImageExposurePage";
import { PlaceholderPage } from "../pages/PlaceholderPage";
import { SecurityCenter } from "../pages/SecurityCenter";
import { ProtectedRoute } from "../components/auth/ProtectedRoute";

export const router = createBrowserRouter([
  { path: "/", element: <Landing /> },
  { path: "/login", element: <Login /> },
  {
    path: "/dashboard",
    element: <ProtectedRoute><CommandCenter /></ProtectedRoute>,
  },
  {
    path: "/investigations/image-exposure",
    element: <ProtectedRoute><ImageExposurePage /></ProtectedRoute>,
  },
  {
    path: "/investigations",
    element: (
      <ProtectedRoute>
        <PlaceholderPage
          title="Investigations"
          subtitle="Active and historical operational intelligence cases."
        />
      </ProtectedRoute>
    ),
  },
  {
    path: "/evidence",
    element: (
      <ProtectedRoute>
        <PlaceholderPage
          title="Evidence Vault"
          subtitle="Cryptographically sealed forensic artifacts and chain of custody."
        />
      </ProtectedRoute>
    ),
  },
  {
    path: "/reports",
    element: (
      <ProtectedRoute>
        <PlaceholderPage
          title="Reports & Dossiers"
          subtitle="Compliance summaries, takedown notices, and executive intelligence."
        />
      </ProtectedRoute>
    ),
  },
  {
    path: "/security",
    element: <ProtectedRoute><SecurityCenter /></ProtectedRoute>,
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);
