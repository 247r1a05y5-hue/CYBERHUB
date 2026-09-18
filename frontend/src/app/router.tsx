import React from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { Login } from "../pages/Login";
import { ImageSearchHome } from "../pages/ImageSearchHome";
import { DatasetPage } from "../pages/DatasetPage";
import { ProtectedRoute } from "../components/auth/ProtectedRoute";
import { ErrorBoundary } from "../components/common/ErrorBoundary";

export const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <ErrorBoundary componentName="ImageSearchHome">
        <ImageSearchHome />
      </ErrorBoundary>
    ),
  },
  {
    path: "/search",
    element: (
      <ErrorBoundary componentName="ImageSearchHome">
        <ImageSearchHome />
      </ErrorBoundary>
    ),
  },
  {
    path: "/search/:id",
    element: (
      <ErrorBoundary componentName="ImageSearchHome">
        <ImageSearchHome />
      </ErrorBoundary>
    ),
  },
  {
    path: "/search/:id/result/:resultId",
    element: (
      <ErrorBoundary componentName="ImageSearchHome">
        <ImageSearchHome />
      </ErrorBoundary>
    ),
  },
  {
    path: "/dataset",
    element: (
      <ProtectedRoute>
        <ErrorBoundary componentName="DatasetPage">
          <DatasetPage />
        </ErrorBoundary>
      </ProtectedRoute>
    ),
  },
  { path: "/login", element: <Login /> },
  { path: "*", element: <Navigate to="/" replace /> },
]);

