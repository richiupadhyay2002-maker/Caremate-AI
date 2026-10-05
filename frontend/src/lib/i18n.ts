"use client";

/**
 * Multilingual scaffold (English + Hindi per the original spec).
 * Only UI chrome is translated; clinical record content stays in English
 * in this build. Language is a UI toggle persisted in localStorage.
 */
import { useApp, Lang } from "./auth-context";

export const STRINGS: Record<Lang, Record<string, string>> = {
  en: {
    appName: "Caremate",
    demoLabel: "DEMO DATA",
    patientPortal: "Patient Portal",
    doctorPortal: "Doctor Portal",
    // patient nav
    navTimeline: "My Care Timeline",
    navAsk: "Ask My Record",
    navReports: "Report Explainer",
    navNutrition: "Nutrition & Diet",
    navJournal: "Symptom Journal",
    navPrep: "Appointment Prep",
    // doctor nav
    navPatients: "Patient List",
    navDoctorAsk: "Ask the Record",
    navRiskWatch: "Risk Watcher",
    // common
    summary: "Summary",
    keyFindings: "Key Findings",
    sources: "Sources",
    missingInfo: "Missing Info",
    safetyStatus: "Safety Status",
    seekCare: "Seek care now",
    signOut: "Sign out",
  },
  hi: {
    appName: "केयरमेट",
    demoLabel: "डेमो डेटा",
    patientPortal: "रोगी पोर्टल",
    doctorPortal: "डॉक्टर पोर्टल",
    navTimeline: "मेरी केयर टाइमलाइन",
    navAsk: "मेरे रिकॉर्ड से पूछें",
    navReports: "रिपोर्ट समझें",
    navNutrition: "पोषण और आहार",
    navJournal: "लक्षण डायरी",
    navPrep: "अपॉइंटमेंट तैयारी",
    navPatients: "रोगी सूची",
    navDoctorAsk: "रिकॉर्ड से पूछें",
    navRiskWatch: "जोखिम निगरानी",
    summary: "सारांश",
    keyFindings: "मुख्य बिंदु",
    sources: "स्रोत",
    missingInfo: "अनुपलब्ध जानकारी",
    safetyStatus: "सुरक्षा स्थिति",
    seekCare: "अभी देखभाल लें",
    signOut: "साइन आउट",
  },
};

export function useT() {
  const { lang } = useApp();
  return (key: string): string => STRINGS[lang][key] ?? STRINGS.en[key] ?? key;
}

export type { Lang };
