import { lazy, Suspense, useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { Skeleton } from "@/components/ui/Skeleton";
import { Toaster } from "@/components/ui/Toaster";
import { ThemeProvider } from "@/context/ThemeContext";
import { ToastProvider } from "@/context/ToastContext";

const OverviewPage = lazy(() =>
  import("@/pages/OverviewPage").then((m) => ({ default: m.OverviewPage })),
);
const LeadsPage = lazy(() =>
  import("@/pages/LeadsPage").then((m) => ({ default: m.LeadsPage })),
);
const SourcesPage = lazy(() =>
  import("@/pages/SourcesPage").then((m) => ({ default: m.SourcesPage })),
);
const ApprovalPage = lazy(() =>
  import("@/pages/ApprovalPage").then((m) => ({ default: m.ApprovalPage })),
);
const SettingsPage = lazy(() =>
  import("@/pages/SettingsPage").then((m) => ({ default: m.SettingsPage })),
);

function PageLoader() {
  return (
    <div className="space-y-4 p-4">
      <Skeleton className="h-10 w-64" />
      <Skeleton className="h-64 w-full rounded-2xl" />
    </div>
  );
}

function Shell() {
  const [cmdOpen, setCmdOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCmdOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return (
    <>
      <AppLayout onOpenCommand={() => setCmdOpen(true)} />
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} />
    </>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Shell />}>
              <Route
                index
                element={
                  <Suspense fallback={<PageLoader />}>
                    <OverviewPage />
                  </Suspense>
                }
              />
              <Route
                path="leads"
                element={
                  <Suspense fallback={<PageLoader />}>
                    <LeadsPage />
                  </Suspense>
                }
              />
              <Route
                path="sources"
                element={
                  <Suspense fallback={<PageLoader />}>
                    <SourcesPage />
                  </Suspense>
                }
              />
              <Route
                path="approval"
                element={
                  <Suspense fallback={<PageLoader />}>
                    <ApprovalPage />
                  </Suspense>
                }
              />
              <Route
                path="settings"
                element={
                  <Suspense fallback={<PageLoader />}>
                    <SettingsPage />
                  </Suspense>
                }
              />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster />
      </ToastProvider>
    </ThemeProvider>
  );
}
