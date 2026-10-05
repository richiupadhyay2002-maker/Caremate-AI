"use client";

import DoctorGate from "@/components/DoctorGate";

/**
 * Route-level gate: every page under /doctors requires an authenticated
 * doctor or admin account. Guests and patient accounts see an access card.
 */
export default function DoctorsLayout({ children }: { children: React.ReactNode }) {
  return <DoctorGate>{children}</DoctorGate>;
}
