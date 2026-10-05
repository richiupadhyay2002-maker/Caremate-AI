"use client";

import { Card } from "@/components/ui";

/**
 * Emergency Warning System banner — shown immediately when a red-flag
 * symptom is detected anywhere in the patient portal.
 */
export default function EmergencyBanner({ message }: { message: string }) {
  return (
    <Card className="border-status-urgent/50 bg-status-urgent-bg/40">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 w-2.5 h-2.5 rounded-full bg-status-urgent flex-shrink-0" />
        <div>
          <h2 className="text-base font-heading text-status-urgent">
            Seek care now
          </h2>
          <p className="text-sm text-ink-primary mt-1">{message}</p>
          <p className="text-xs text-ink-secondary mt-2">
            Contact your care team&apos;s emergency line or your local emergency
            number immediately. Do not wait for your next appointment, and do
            not rely on this website for urgent care.
          </p>
        </div>
      </div>
    </Card>
  );
}
