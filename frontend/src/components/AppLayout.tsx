"use client";

import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";
import AppSidebar from "@/components/AppSidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth();
  const showSidebar = !!token && !loading;

  return (
    <>
      {showSidebar && <AppSidebar />}
      <main
        className={cn(
          "min-h-screen bg-clinical-bg transition-margin duration-200",
          showSidebar ? "ml-[230px]" : "ml-0",
        )}
      >
        <div className="max-w-[920px] mx-auto px-6 pt-7">
          {children}
        </div>
      </main>
    </>
  );
}
