/**
 * DEMO DATA — not real medical records.
 * Synthetic patient histories styled after open formats such as Synthea
 * and public patient-education content (MedlinePlus / NCI). All names,
 * identifiers and clinical values are fictional.
 */

export interface DemoMedication {
  name: string;
  dosage: string;
  frequency: string;
  started: string;
}

export interface DemoDocSection {
  heading: string;
  text: string;
}

export interface DemoDocument {
  id: string;
  patient_id: string;
  title: string;
  type: "pathology" | "radiology" | "lab" | "visit" | "discharge";
  source: string;
  date: string;
  sections: DemoDocSection[];
}

export interface DemoLab {
  patient_id: string;
  date: string;
  albumin_g_dl: number;
  hemoglobin_g_dl: number;
  creatinine_mg_dl: number;
  crp_mg_l: number;
}

export interface DemoAppointment {
  id: string;
  patient_id: string;
  title: string;
  clinician: string;
  location: string;
  date: string;
  notes: string;
}

export interface DemoWeightEntry {
  patient_id: string;
  date: string;
  weight_kg: number;
}

export interface DemoPatient {
  id: string;
  name: string;
  age: number;
  sex: string;
  diagnosis: string;
  diagnosis_details: string;
  medications: DemoMedication[];
  allergies: { substance: string; reaction: string; severity: string }[];
  dietary_restrictions: string[];
  appetite: "good" | "reduced" | "poor";
  height_cm: number;
  stage_note: string;
  // First-person documented history used by AI-grounded answers
  history_events: { date: string; event: string; detail: string }[];
}

export const DEMO_PATIENTS: DemoPatient[] = [
  {
    id: "P0001",
    name: "Asha Verma",
    age: 58,
    sex: "Female",
    diagnosis: "Breast cancer, Stage II (ER+/PR+, HER2-negative)",
    diagnosis_details:
      "Invasive ductal carcinoma of the left breast, diagnosed 14 months ago. Status post lumpectomy with sentinel lymph node biopsy (2 of 14 nodes positive). Completed adjuvant chemotherapy; currently on endocrine therapy and radiation follow-up.",
    medications: [
      { name: "Tamoxifen", dosage: "20 mg", frequency: "Once daily", started: "2025-06-02" },
      { name: "Letrozole", dosage: "2.5 mg", frequency: "Once daily (was switched)", started: "2025-08-15" },
      { name: "Calcium + Vitamin D", dosage: "500 mg / 400 IU", frequency: "Twice daily", started: "2025-07-01" },
    ],
    allergies: [{ substance: "Penicillin", reaction: "Rash", severity: "Moderate" }],
    dietary_restrictions: ["Lactose intolerance"],
    appetite: "reduced",
    height_cm: 160,
    stage_note: "On adjuvant endocrine therapy; surveillance imaging every 6 months.",
    history_events: [
      { date: "2025-04-18", event: "Lumpectomy performed", detail: "Wide local excision of left breast lesion; sentinel node biopsy showed 2/14 nodes positive." },
      { date: "2025-05-30", event: "Adjuvant chemotherapy completed", detail: "4 cycles AC-T regimen completed. Neuropathy grade 1 in fingertips noted at completion visit." },
      { date: "2025-08-15", event: "Endocrine therapy switched", detail: "Tamoxifen-related leg cramps led oncologist to switch to letrozole (aromatase inhibitor)." },
      { date: "2025-12-04", event: "Follow-up visit", detail: "Reports reduced appetite since chemotherapy; weight down 4% from baseline. Dietitian referral suggested and accepted." },
      { date: "2026-02-20", event: "Surveillance mammogram", detail: "No suspicious findings on left breast; right breast BI-RADS 2 (benign findings)." },
    ],
  },
  {
    id: "P0002",
    name: "Rahul Mehta",
    age: 47,
    sex: "Male",
    diagnosis: "Colorectal cancer, Stage III",
    diagnosis_details:
      "Adenocarcinoma of the sigmoid colon, diagnosed 9 months ago. Status post left hemicolectomy with 3 of 21 regional nodes positive. Currently receiving adjuvant FOLFOX chemotherapy, cycle 6 of 12.",
    medications: [
      { name: "Oxaliplatin", dosage: "85 mg/m2", frequency: "IV, every 2 weeks", started: "2025-09-10" },
      { name: "Leucovorin", dosage: "400 mg/m2", frequency: "IV, every 2 weeks", started: "2025-09-10" },
      { name: "5-Fluorouracil", dosage: "bolus + infusion", frequency: "IV, every 2 weeks", started: "2025-09-10" },
      { name: "Ondansetron", dosage: "8 mg", frequency: "As needed for nausea", started: "2025-09-10" },
    ],
    allergies: [{ substance: "None known", reaction: "—", severity: "—" }],
    dietary_restrictions: [],
    appetite: "poor",
    height_cm: 174,
    stage_note: "Cycle 6 of 12 adjuvant FOLFOX; oxaliplatin-related cold sensitivity developing.",
    history_events: [
      { date: "2025-07-02", event: "Diagnosis — colonoscopy biopsy", detail: "Biopsy of sigmoid lesion: invasive adenocarcinoma, moderately differentiated." },
      { date: "2025-08-21", event: "Left hemicolectomy", detail: "Laparoscopic resection, 21 nodes harvested, 3 positive (pT3 N1b)." },
      { date: "2025-09-10", event: "Adjuvant FOLFOX started", detail: "Baseline CEA 6.8 ng/mL; port placed." },
      { date: "2026-01-14", event: "Mid-treatment labs", detail: "Albumin 3.2 g/dL (low-normal), weight down 6% from baseline, persistent tingling in fingers when touching cold items." },
      { date: "2026-03-05", event: "Oncology review", detail: "Neuropathy grade 2 discussed; dose reduction considered at next cycle." },
    ],
  },
  {
    id: "P0003",
    name: "Meera Nair",
    age: 66,
    sex: "Female",
    diagnosis: "Early-stage lung nodule surveillance",
    diagnosis_details:
      "Incidental 7 mm right lower lobe nodule on CT. No malignancy diagnosed. In a structured CT surveillance program (12-month interval). History of hypothyroidism.",
    medications: [
      { name: "Levothyroxine", dosage: "50 mcg", frequency: "Once daily, fasting", started: "2019-03-11" },
      { name: "Atorvastatin", dosage: "10 mg", frequency: "Once daily", started: "2022-11-08" },
    ],
    allergies: [{ substance: "Sulfa drugs", reaction: "Hives", severity: "Severe" }],
    dietary_restrictions: [],
    appetite: "good",
    height_cm: 155,
    stage_note: "No cancer diagnosis. Surveillance only.",
    history_events: [
      { date: "2025-10-09", event: "Incidental nodule found", detail: "7 mm solid nodule, right lower lobe, found on CT done for persistent cough. Lung-RADS 3." },
      { date: "2026-01-15", event: "Pulmonology consult", detail: "Plan: repeat low-dose CT in 12 months; no biopsy indicated at this size." },
      { date: "2026-03-02", event: "Annual physical", detail: "TSH 2.1 (on levothyroxine), stable. Cough resolved." },
    ],
  },
  {
    id: "P0004",
    name: "Sanjay Gupta",
    age: 71,
    sex: "Male",
    diagnosis: "Head and neck cancer (post-treatment), under nutrition review",
    diagnosis_details:
      "Squamous cell carcinoma of the larynx, treated 18 months ago with chemoradiation. Currently has radiation-related swallowing difficulty and significant weight loss under dietitian review.",
    medications: [
      { name: "Pregabalin", dosage: "75 mg", frequency: "Twice daily", started: "2025-11-01" },
      { name: "Levothyroxine", dosage: "75 mcg", frequency: "Once daily", started: "2025-10-05" },
      { name: "Sucralfate", dosage: "1 g", frequency: "Before meals", started: "2026-01-20" },
    ],
    allergies: [{ substance: "Aspirin", reaction: "Asthma exacerbation", severity: "Severe" }],
    dietary_restrictions: ["Soft/semi-solid diet recommended after radiation", "No aspirin"],
    appetite: "poor",
    height_cm: 168,
    stage_note: "Post-radiation follow-up; hypothyroidism after neck radiation (on replacement).",
    history_events: [
      { date: "2024-08-12", event: "Chemoradiation completed", detail: "70 Gy in 35 fractions + weekly cisplatin completed for laryngeal SCC." },
      { date: "2025-10-05", event: "Radiation-induced hypothyroidism", detail: "TSH 12.4, started levothyroxine replacement." },
      { date: "2026-01-22", event: "Nutrition review", detail: "Weight down 9% in 6 months. Albumin 3.1 g/dL. Odynophagia limiting solid intake; dietitian program started." },
      { date: "2026-02-28", event: "Dysphagia clinic", detail: "Modified barium swallow: mild aspiration risk with thin liquids; thickened liquids advised." },
    ],
  },
];

export const DEMO_DOCUMENTS: DemoDocument[] = [
  // --- P0001 Asha ---
  {
    id: "D-P1-001",
    patient_id: "P0001",
    title: "Pathology Report — Lumpectomy (Left Breast)",
    type: "pathology",
    source: "Department of Pathology (demo)",
    date: "2025-04-22",
    sections: [
      { heading: "Specimen", text: "Left breast lumpectomy with sentinel lymph nodes (14 nodes submitted)." },
      { heading: "Diagnosis", text: "Invasive ductal carcinoma, grade 2, with 2 of 14 sentinel lymph nodes positive. Tumor size 2.1 cm. Estrogen receptor positive (strong, 95%), progesterone receptor positive, HER2 negative." },
      { heading: "Margins", text: "All surgical margins clear of tumor; closest margin 6 mm." },
      { heading: "Lymphovascular invasion", text: "Present, focal." },
      { heading: "Not addressed in this report", text: "This report does not describe distant organs such as liver, lung or bone; it covers the breast tissue and lymph nodes removed in this surgery only." },
    ],
  },
  {
    id: "D-P1-002",
    patient_id: "P0001",
    title: "Lab Results — Routine Surveillance",
    type: "lab",
    source: "Central Diagnostics Lab (demo)",
    date: "2026-01-19",
    sections: [
      { heading: "Hemogram", text: "Hemoglobin 11.8 g/dL (slightly below the 12.0 reference for women). White cell count and platelets within normal limits." },
      { heading: "Chemistry", text: "Albumin 3.6 g/dL (low-normal). Creatinine 0.9 mg/dL (normal). Liver enzymes normal." },
      { heading: "Interpretation", text: "Mild anemia of inflammation suspected. No urgent abnormality." },
    ],
  },
  {
    id: "D-P1-003",
    patient_id: "P0001",
    title: "Radiology Report — Diagnostic Mammogram (Bilateral)",
    type: "radiology",
    source: "Imaging Centre (demo)",
    date: "2026-02-20",
    sections: [
      { heading: "Technique", text: "Bilateral digital mammography with tomosynthesis." },
      { heading: "Findings", text: "Left breast: post-surgical scarring and architectural distortion, stable compared with prior. Right breast: benign-appearing calcifications, BI-RADS category 2." },
      { heading: "Impression", text: "No evidence of recurrence in the treated left breast. Right breast findings benign. BI-RADS 2 overall. Recommend routine screening." },
      { heading: "Not addressed in this report", text: "A mammogram images the breast only. It cannot detect disease in the abdomen, chest, bones, or blood, and does not replace blood tests or a physical examination." },
    ],
  },
  {
    id: "D-P1-004",
    patient_id: "P0001",
    title: "Oncology Visit Note — Follow-up",
    type: "visit",
    source: "Medical Oncology OPD (demo)",
    date: "2025-12-04",
    sections: [
      { heading: "History", text: "Reports reduced appetite since completing chemotherapy, especially in the mornings. Weight 61.5 kg, down approximately 4% from baseline 64 kg." },
      { heading: "Assessment", text: "Stable on letrozole. Leg cramps on tamoxifen resolved after switch. Mild early satiety." },
      { heading: "Plan", text: "Dietitian referral placed. Continue letrozole, calcium and vitamin D. Repeat labs before next visit." },
    ],
  },

  // --- P0002 Rahul ---
  {
    id: "D-P2-001",
    patient_id: "P0002",
    title: "Pathology Report — Colectomy Specimen",
    type: "pathology",
    source: "Department of Pathology (demo)",
    date: "2025-08-25",
    sections: [
      { heading: "Specimen", text: "Left hemicolectomy with regional lymph nodes (21 nodes examined)." },
      { heading: "Diagnosis", text: "Adenocarcinoma of the sigmoid colon, moderately differentiated, invading through the muscular wall (pT3). Three of twenty-one regional lymph nodes positive (N1b). No margin involvement." },
      { heading: "Stage", text: "Pathologic stage III (T3 N1b M0 by TNM 8th edition)." },
      { heading: "Not addressed in this report", text: "This report describes only the surgically removed tissue. It does not tell whether chemotherapy is needed — that decision was made later by the oncology team using this report together with other information." },
    ],
  },
  {
    id: "D-P2-002",
    patient_id: "P0002",
    title: "Lab Results — Mid-chemotherapy Panel",
    type: "lab",
    source: "Central Diagnostics Lab (demo)",
    date: "2026-01-14",
    sections: [
      { heading: "Hemogram", text: "Hemoglobin 10.4 g/dL (below reference range). Neutrophils low-normal. Platelets normal." },
      { heading: "Chemistry", text: "Albumin 3.2 g/dL (low). Creatinine 1.0 mg/dL (normal). Magnesium low-normal." },
      { heading: "Tumour marker", text: "CEA 4.1 ng/mL, down from 6.8 ng/mL at start of treatment." },
    ],
  },
  {
    id: "D-P2-003",
    patient_id: "P0002",
    title: "Oncology Visit Note — Cycle 6 Review",
    type: "visit",
    source: "Medical Oncology Daycare (demo)",
    date: "2026-03-05",
    sections: [
      { heading: "History", text: "Cold-triggered tingling in fingers (oxaliplatin neuropathy) worsening; uses gloves for refrigerated items. Appetite poor; weight 68.9 kg from baseline 73.5 kg (−6%)." },
      { heading: "Assessment", text: "Oxaliplatin-induced peripheral neuropathy, grade 2. Treatment-related anemia." },
      { heading: "Plan", text: "Consider oxaliplatin dose reduction at cycle 7. Dietitian referral. Monitor CEA per schedule." },
    ],
  },

  // --- P0003 Meera ---
  {
    id: "D-P3-001",
    patient_id: "P0003",
    title: "Radiology Report — CT Chest",
    type: "radiology",
    source: "Imaging Centre (demo)",
    date: "2025-10-09",
    sections: [
      { heading: "Technique", text: "Non-contrast CT chest." },
      { heading: "Findings", text: "7 mm solid nodule in the right lower lobe with smooth margins. No calcified pattern suspicious for cancer. No enlarged lymph nodes. No pleural effusion." },
      { heading: "Impression", text: "Solitary pulmonary nodule, Lung-RADS category 3 — probably benign, but below the threshold where biopsy is standard. Follow-up imaging in 12 months recommended." },
      { heading: "Not addressed in this report", text: "This scan cannot rule out disease outside the chest, and a single image cannot prove a nodule is benign — that is why follow-up imaging is advised." },
    ],
  },
  {
    id: "D-P3-002",
    patient_id: "P0003",
    title: "Pulmonology Consult Note",
    type: "visit",
    source: "Pulmonology OPD (demo)",
    date: "2026-01-15",
    sections: [
      { heading: "History", text: "Persistent cough for 6 weeks, resolved now. Never smoker." },
      { heading: "Plan", text: "Low-dose CT surveillance in 12 months. No biopsy at this size unless growth is seen." },
    ],
  },

  // --- P0004 Sanjay ---
  {
    id: "D-P4-001",
    patient_id: "P0004",
    title: "Lab Results — Nutrition Panel",
    type: "lab",
    source: "Central Diagnostics Lab (demo)",
    date: "2026-01-22",
    sections: [
      { heading: "Nutrition markers", text: "Albumin 3.1 g/dL (low). Prealbumin 12 mg/dL (low). Hemoglobin 10.9 g/dL." },
      { heading: "Thyroid", text: "TSH 3.0 on levothyroxine replacement — adequately treated." },
    ],
  },
  {
    id: "D-P4-002",
    patient_id: "P0004",
    title: "Radiology Report — Modified Barium Swallow",
    type: "radiology",
    source: "Imaging Centre (demo)",
    date: "2026-02-28",
    sections: [
      { heading: "Findings", text: "Mild aspiration of thin liquids; swallowing improves with thickened liquids. No obstruction. Pharyngeal transit mildly delayed." },
      { heading: "Impression", text: "Radiation-related dysphagia with thin-liquid aspiration risk. Thickened liquids and swallow therapy advised." },
      { heading: "Not addressed in this report", text: "This study examines swallowing only. It does not assess tumour status or nutrition beyond the moment of the test." },
    ],
  },
];

export const DEMO_LABS: DemoLab[] = [
  { patient_id: "P0001", date: "2025-12-04", albumin_g_dl: 3.8, hemoglobin_g_dl: 12.2, creatinine_mg_dl: 0.9, crp_mg_l: 4 },
  { patient_id: "P0001", date: "2026-01-19", albumin_g_dl: 3.6, hemoglobin_g_dl: 11.8, creatinine_mg_dl: 0.9, crp_mg_l: 6 },
  { patient_id: "P0002", date: "2025-10-15", albumin_g_dl: 3.7, hemoglobin_g_dl: 11.6, creatinine_mg_dl: 1.0, crp_mg_l: 9 },
  { patient_id: "P0002", date: "2026-01-14", albumin_g_dl: 3.2, hemoglobin_g_dl: 10.4, creatinine_mg_dl: 1.0, crp_mg_l: 14 },
  { patient_id: "P0003", date: "2026-03-02", albumin_g_dl: 4.2, hemoglobin_g_dl: 13.1, creatinine_mg_dl: 0.8, crp_mg_l: 2 },
  { patient_id: "P0004", date: "2025-11-22", albumin_g_dl: 3.5, hemoglobin_g_dl: 11.2, creatinine_mg_dl: 1.1, crp_mg_l: 10 },
  { patient_id: "P0004", date: "2026-01-22", albumin_g_dl: 3.1, hemoglobin_g_dl: 10.9, creatinine_mg_dl: 1.2, crp_mg_l: 16 },
];

export const DEMO_APPOINTMENTS: DemoAppointment[] = [
  { id: "A-P1-001", patient_id: "P0001", title: "Medical Oncology — 3-month follow-up", clinician: "Dr. K. Sharma (demo)", location: "OPD, Level 2", date: "2026-05-11", notes: "Bring medication list; repeat CBC and albumin requested." },
  { id: "A-P2-001", patient_id: "P0002", title: "Chemotherapy — Cycle 7 (FOLFOX)", clinician: "Daycare Unit", location: "Daycare, Level 1", date: "2026-03-19", notes: "Dose-reduction decision pending; report cold sensitivity." },
  { id: "A-P3-001", patient_id: "P0003", title: "Pulmonology — surveillance review", clinician: "Dr. R. Iyer (demo)", location: "OPD, Level 3", date: "2026-06-02", notes: "Annual CT booked for the same week." },
  { id: "A-P4-001", patient_id: "P0004", title: "Nutrition Clinic review", clinician: "Ms. S. Rao, dietitian (demo)", location: "Dietetics, Ground floor", date: "2026-03-24", notes: "Weight trend and swallow therapy progress." },
];

export const DEMO_WEIGHTS: DemoWeightEntry[] = [
  { patient_id: "P0001", date: "2025-06-01", weight_kg: 64.0 },
  { patient_id: "P0001", date: "2025-12-04", weight_kg: 61.5 },
  { patient_id: "P0002", date: "2025-09-10", weight_kg: 73.5 },
  { patient_id: "P0002", date: "2026-03-05", weight_kg: 68.9 },
  { patient_id: "P0003", date: "2026-03-02", weight_kg: 58.2 },
  { patient_id: "P0004", date: "2025-07-30", weight_kg: 66.0 },
  { patient_id: "P0004", date: "2026-01-22", weight_kg: 60.1 },
];

export function getPatient(id: string): DemoPatient | undefined {
  return DEMO_PATIENTS.find((p) => p.id === id);
}

export function getDocuments(patientId: string): DemoDocument[] {
  return DEMO_DOCUMENTS.filter((d) => d.patient_id === patientId);
}

export function getLabs(patientId: string): DemoLab[] {
  return DEMO_LABS.filter((l) => l.patient_id === patientId);
}

export function getAppointment(patientId: string): DemoAppointment | undefined {
  return DEMO_APPOINTMENTS.find((a) => a.patient_id === patientId);
}

export function getWeights(patientId: string): DemoWeightEntry[] {
  return DEMO_WEIGHTS.filter((w) => w.patient_id === patientId);
}

/** Weight-loss percentage between first and most recent recorded weight. */
export function weightLossPercent(patientId: string): number | null {
  const w = getWeights(patientId);
  if (w.length < 2) return null;
  const first = w[0].weight_kg;
  const last = w[w.length - 1].weight_kg;
  return Math.round(((first - last) / first) * 1000) / 10;
}
