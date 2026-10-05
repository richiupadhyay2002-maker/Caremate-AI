/**
 * Prototype-stage AI engine (mock/template logic).
 *
 * The production pipeline (retrieval → summarization → citation check →
 * safety check → response) lives in the Python backend; this module provides
 * deterministic template-based equivalents so the deployed demo works with
 * zero API keys. Every answer is grounded strictly in the patient's own demo
 * records and returns the shared structured shape:
 *   Summary → Key Findings → Sources → Missing Info → Safety Status
 */
import {
  DEMO_DOCUMENTS,
  getPatient,
  getDocuments,
  getLabs,
  getAppointment,
  weightLossPercent,
  type DemoDocument,
} from "./demo-data";

// ---------------------------------------------------------------- types
export type SafetyCategory =
  | "safe_information"
  | "needs_clinician_review"
  | "urgent_medical_attention"
  | "insufficient_information"
  | "disallowed_medical_advice";

export const SAFETY_LABELS: Record<SafetyCategory, string> = {
  safe_information: "Safe Information",
  needs_clinician_review: "Needs Clinician Review",
  urgent_medical_attention: "Urgent Medical Attention",
  insufficient_information: "Insufficient Information",
  disallowed_medical_advice: "Disallowed Medical Advice",
};

export const SAFETY_EXPLAIN: Record<SafetyCategory, string> = {
  safe_information: "General, non-actionable information drawn from your own records.",
  needs_clinician_review: "Content that a doctor or nurse should confirm before you act on it.",
  urgent_medical_attention: "A warning sign that needs prompt medical contact.",
  insufficient_information: "Your records do not contain enough information to answer reliably.",
  disallowed_medical_advice: "This request asks for a diagnosis or treatment decision, which CareMate never provides.",
};

export interface Citation {
  document_id: string;
  document_title: string;
  section: string;
  snippet: string;
}

export interface StructuredAnswer {
  question: string;
  summary: string;
  key_findings: string[];
  citations: Citation[];
  missing_info: string[];
  safety: SafetyCategory;
  safety_note: string;
  generator: "template-v1" | "backend-rag";
  /** Jargon found in the answer, explained for a non-medical reader. */
  plain_terms?: { term: string; meaning: string }[];
}

// ------------------------------------------------------- red-flag symptoms
const RED_FLAGS: { pattern: RegExp; message: string }[] = [
  { pattern: /chest pain|pressure in (my )?chest/i, message: "Chest pain can signal a serious heart or lung problem." },
  { pattern: /(difficulty|trouble|shortness of) breath(ing)?|can'?t breathe|gasping/i, message: "Difficulty breathing needs urgent assessment." },
  { pattern: /cough(ing)? (up )?blood|blood in (my )?sputum|haemoptysis|hemoptysis/i, message: "Coughing up blood requires immediate medical contact." },
  { pattern: /severe bleeding|bleeding (that )?won'?t stop|blood in (my )?stool.*(a lot|heavy)?/i, message: "Uncontrolled bleeding is an emergency." },
  { pattern: /passing out|fainted|unconscious|black(ed)? out/i, message: "Fainting or blackouts need urgent evaluation." },
  { pattern: /confusion|disoriented|slurred speech|face droop|weak(ness)? on one side/i, message: "Sudden confusion or one-sided weakness can indicate a stroke — act immediately." },
  { pattern: /suicid|kill myself|end my life|self harm/i, message: "If you are thinking of harming yourself, please contact a crisis line or emergency services right away." },
  { pattern: /high fever (of )?(10[3-9]|4[0-9])/i, message: "A fever above 103°F/39.4°C needs prompt medical contact, especially during cancer treatment." },
  { pattern: /fever.*(neutropenia|chemotherapy|chemo)|chemo.*fever/i, message: "Fever during chemotherapy is an emergency — contact your oncology team or emergency services immediately." },
  { pattern: /sudden (severe )?(worst )?headache/i, message: "A sudden severe headache needs immediate medical assessment." },
];

export function detectRedFlag(text: string): string | null {
  for (const f of RED_FLAGS) {
    if (f.pattern.test(text)) return f.message;
  }
  return null;
}

// ------------------------------------------------ drug–food interactions
const DRUG_FOOD: {
  drug: RegExp;
  foods: string;
  advice: string;
}[] = [
  {
    drug: /warfarin/i,
    foods: "foods high in vitamin K (spinach, kale, broccoli)",
    advice: "keep vitamin-K foods consistent rather than avoiding them, and tell your care team before changing your diet",
  },
  {
    drug: /grapefruit|statin|atorvastatin|simvastatin/i,
    foods: "grapefruit and grapefruit juice",
    advice: "grapefruit can raise blood levels of some statins and other drugs — check with your pharmacist",
  },
  {
    drug: /metronidazole/i,
    foods: "alcohol",
    advice: "avoid alcohol completely while taking metronidazole and for 48 hours after",
  },
  {
    drug: /tetracycline|doxycycline|ciprofloxacin|levothyroxine/i,
    foods: "calcium supplements, milk, antacids",
    advice: "these can block absorption — separate them from the medicine by several hours (levothyroxine is taken fasting for this reason)",
  },
  {
    drug: /tyramine|maoi|phenelzine/i,
    foods: "aged cheese, cured meats, fermented foods",
    advice: "aged/fermented foods high in tyramine can interact dangerously with MAO inhibitors",
  },
  {
    drug: /tamoxifen|letrozole/i,
    foods: "no specific food restriction in your records",
    advice: "no major food–drug interaction is recorded; the general rule is to take it the same way each day and mention herbal supplements to your oncologist",
  },
  {
    drug: /5-fluorouracil|oxaliplatin|folfox/i,
    foods: "cold foods and drinks",
    advice: "cold items can trigger the nerve-related tingling caused by oxaliplatin; room-temperature alternatives are commonly suggested by care teams during infusion days",
  },
];

// --------------------------------------------------------- helpers
/**
 * Layman-language explanations for medical terms that may appear in an
 * answer or report. Written so a reader with no medical or biology
 * background can understand them.
 */
const TERM_MEANINGS: Record<string, string> = {
  "invasive ductal carcinoma":
    "the most common type of breast cancer; 'invasive' means it has grown beyond the milk duct where it started",
  "grade 2":
    "an intermediate growth speed — the cells look neither very slow-growing nor very aggressive under the microscope",
  "sentinel lymph node":
    "the first lymph node (a small filter station of the immune system) that fluid from the tumor reaches; testing it shows whether cancer has started to spread",
  "her2 negative":
    "HER2 is a protein that can help some cancer cells grow faster. 'HER2 negative' means the test did not find a high amount of this protein in the tested sample, so HER2-targeting drugs would not help",
  "her2 positive":
    "the test found a high amount of the HER2 protein, which can make cancer cells grow faster — special drugs that block this protein can work",
  "er+":
    "the cancer cells carry a 'door' for the hormone oestrogen, so medicines that block oestrogen are likely to help",
  "pr+":
    "the cancer cells carry a similar 'door' for the hormone progesterone — another sign hormone-blocking medicines can help",
  "hormone receptor":
    "a 'door' on the outside of a cell that hormones use as a signal to make the cell grow",
  "margins clear":
    "the outer edge of the removed tissue had no cancer cells, which suggests the tumor was fully removed",
  "lymphovascular invasion":
    "a few cancer cells were seen entering tiny blood or lymph channels — doctors weigh this when planning further treatment",
  "pt3":
    "the tumor had grown through the muscle wall of the bowel",
  "n1b":
    "cancer was found in several nearby lymph nodes",
  "adenocarcinoma":
    "a cancer that starts in the cells that make mucus or fluids, the usual type in the colon",
  "cea":
    "a blood marker that can rise with some bowel cancers; how it changes over time matters more than one single value",
  "bi-rads 2":
    "a mammogram scoring category that means the findings are definitely benign (non-cancerous)",
  "lung-rads 3":
    "a lung CT scoring category meaning the nodule is probably harmless but should be re-imaged to confirm it is not growing",
  "albumin":
    "a protein made by the liver that keeps fluid in the blood vessels; doctors use it as a rough sign of overall nutrition",
  "hemoglobin":
    "the part of red blood cells that carries oxygen around the body; low levels cause tiredness and weakness",
  "aspiration":
    "food or liquid going toward the airway (windpipe) instead of the food pipe",
  "dysphagia":
    "difficulty swallowing",
  "odynophagia":
    "pain when swallowing",
  "benign":
    "not cancer — a growth that does not spread to other parts of the body",
  "malignant":
    "cancerous — able to grow into nearby tissue and spread",
  "biopsy":
    "taking a tiny piece of tissue so it can be examined under a microscope",
  "metastasis":
    "cancer that has spread from where it started to another part of the body",
  "prognosis":
    "the likely course and outcome of an illness",
  "remission":
    "signs of the cancer have reduced or disappeared, though it may not be fully gone",
  "neutropenia":
    "too few of the white blood cells that fight bacteria, which makes infections more likely",
  "creatinine":
    "a waste product in the blood used to check how well the kidneys are working",
  "inflammation":
    "the body's natural response to injury or illness — often causing swelling, warmth or pain",
  "tomosynthesis":
    "an advanced mammogram that takes images in thin slices, like a CT scan for the breast",
  "architectural distortion":
    "an area where the normal pattern of breast tissue looks unusual, which doctors examine closely",
  "calcifications":
    "tiny calcium deposits in the breast tissue, visible on a mammogram — most are harmless",
};

/**
 * Find medical terms present in *text* and return layman explanations,
 * longest-first so "her2 negative" wins over "her2"-style overlaps.
 */
export function findTermExplanations(
  text: string,
  max = 6
): { term: string; meaning: string }[] {
  const lower = text.toLowerCase();
  const found: { term: string; meaning: string }[] = [];
  for (const [term, meaning] of Object.entries(TERM_MEANINGS)) {
    if (lower.includes(term.toLowerCase())) {
      found.push({ term, meaning });
    }
  }
  return found
    .sort((a, b) => b.term.length - a.term.length)
    .slice(0, max);
}

function docCitation(doc: DemoDocument, sectionHeading: string): Citation | null {
  const sec = doc.sections.find((s) => s.heading === sectionHeading);
  if (!sec) return null;
  return {
    document_id: doc.id,
    document_title: doc.title,
    section: sec.heading,
    snippet: sec.text.slice(0, 220),
  };
}

function searchDocs(patientId: string, question: string) {
  const words = question.toLowerCase().split(/\W+/).filter((w) => w.length > 3);
  const docs = getDocuments(patientId);
  const scored: { doc: DemoDocument; heading: string; text: string; score: number }[] = [];
  for (const doc of docs) {
    for (const sec of doc.sections) {
      const hay = (doc.title + " " + sec.heading + " " + sec.text).toLowerCase();
      let score = 0;
      for (const w of words) if (hay.includes(w)) score++;
      if (score > 0) scored.push({ doc, heading: sec.heading, text: sec.text, score });
    }
  }
  return scored.sort((a, b) => b.score - a.score).slice(0, 4);
}

function emptyAnswer(question: string): StructuredAnswer {
  return {
    question,
    summary:
      "Your demo records do not contain information that answers this question. I will not fill the gap with general web knowledge — that is a deliberate safety rule.",
    key_findings: [],
    citations: [],
    missing_info: [
      "No matching document, lab result, or visit note was found in the demo record for this topic.",
    ],
    safety: "insufficient_information",
    safety_note: SAFETY_EXPLAIN.insufficient_information,
    generator: "template-v1",
  };
}

// --------------------------------------------------------------- Q&A
export function askRecord(patientId: string, question: string): StructuredAnswer {
  const patient = getPatient(patientId);
  if (!patient) return emptyAnswer(question);

  // 1) Disallowed: diagnosis / treatment decisions
  if (/\b(do i have|what cancer should|should i (take|stop|switch|start)|recommend a treatment|which treatment|what dose)\b/i.test(question)) {
    return {
      question,
      summary:
        "I can explain what your records say, but I cannot diagnose you or tell you which treatment to choose — that decision belongs to you and your care team together.",
      key_findings: [
        "CareMate summarises and explains records only; it never makes diagnosis or treatment decisions.",
      ],
      citations: [],
      missing_info: [
        "A clinical decision requires your oncologist's assessment, which is outside what this tool can do.",
      ],
      safety: "disallowed_medical_advice",
      safety_note: SAFETY_EXPLAIN.disallowed_medical_advice,
      generator: "template-v1",
    };
  }

  // 2) Red-flag short-circuit
  const red = detectRedFlag(question);
  if (red) {
    return {
      question,
      summary: red,
      key_findings: [
        "This symptom pattern is on the emergency warning list.",
        "Contact your care team's emergency line, or emergency services, now — do not wait for your next appointment.",
      ],
      citations: [],
      missing_info: ["The on-call clinical team's triage, which no automated tool can replace."],
      safety: "urgent_medical_attention",
      safety_note: SAFETY_EXPLAIN.urgent_medical_attention,
      generator: "template-v1",
    };
  }

  // 3) Grounded retrieval over demo docs
  const hits = searchDocs(patientId, question);
  if (hits.length === 0) return emptyAnswer(question);

  const citations = hits
    .map((h) => ({ doc: h.doc, heading: h.heading }))
    .map((h) => docCitation(h.doc, h.heading))
    .filter((c): c is Citation => c !== null);

  const summary =
    `Based on the documents in your record, here is what is documented about “${question.replace(/\?+$/, "")}”:\n\n` +
    hits
      .slice(0, 3)
      .map((h) => `• ${h.doc.title} (${h.doc.date}) — ${h.text}`)
      .join("\n\n") +
    `\n\nEverything above comes only from your own records. If anything is unclear, raise it with your care team.`;
  const keyFindings = hits.slice(0, 3).map((h) => `${h.heading}: ${h.text}`);

  return {
    question,
    summary,
    key_findings: keyFindings,
    citations,
    missing_info: [
      "Your care team's interpretation of these findings (plan discussions are not transcribed into the record).",
      "Any documents from before the demo period.",
    ],
    safety: "safe_information",
    safety_note: SAFETY_EXPLAIN.safe_information,
    plain_terms: findTermExplanations(
      summary + " " + keyFindings.join(" ")
    ),
    generator: "template-v1",
  };
}

// ------------------------------------------------------ report explainer
export interface ReportExplanation {
  document_title: string;
  date: string;
  plain_summary: string;
  term_explanations: { term: string; meaning: string }[];
  explicitly_not_said: string[];
  citations: Citation[];
  safety: SafetyCategory;
  safety_note: string;
}

export function explainReport(docId: string): ReportExplanation | null {
  const real = DEMO_DOCUMENTS.find((d) => d.id === docId);
  if (!real) return null;

  const term_explanations = findTermExplanations(
    real.sections.map((s) => s.text).join(" "),
    12
  );

  const explicitly_not_said = real.sections
    .filter((s) => /not addressed|not told|does not/i.test(s.text) || /not addressed/i.test(s.heading))
    .map((s) => s.text);

  const diagnosisSec = real.sections.find((s) => /diagnosis|impression|findings/i.test(s.heading));

  return {
    document_title: real.title,
    date: real.date,
    plain_summary: diagnosisSec
      ? `In plain language: ${diagnosisSec.text}`
      : real.sections[0].text,
    term_explanations,
    explicitly_not_said:
      explicitly_not_said.length > 0
        ? explicitly_not_said
        : ["This report format does not include an explicit limitations statement."],
    citations: real.sections.slice(0, 3).map((s) => ({
      document_id: real.id,
      document_title: real.title,
      section: s.heading,
      snippet: s.text.slice(0, 220),
    })),
    safety: "needs_clinician_review",
    safety_note:
      "A plain-language rewording can lose nuance. Always confirm your understanding of a report with the doctor who ordered it.",
  };
}

// ------------------------------------------------------- nutrition Q&A
export function nutritionAnswer(patientId: string, question: string): StructuredAnswer {
  const patient = getPatient(patientId);
  if (!patient) return emptyAnswer(question);

  const red = detectRedFlag(question);
  if (red) {
    return {
      question,
      summary: red,
      key_findings: ["This is a medical emergency concern, not a nutrition question."],
      citations: [],
      missing_info: [],
      safety: "urgent_medical_attention",
      safety_note: SAFETY_EXPLAIN.urgent_medical_attention,
      generator: "template-v1",
    };
  }

  const meds = patient.medications;
  const findings: string[] = [];
  const citations: Citation[] = [];
  let safety: SafetyCategory = "safe_information";

  for (const m of meds) {
    const match = DRUG_FOOD.find((d) => d.drug.test(m.name));
    if (match) {
      findings.push(
        `You are recorded as taking ${m.name} ${m.dosage}. Regarding ${match.foods}: ${match.advice}.`,
      );
      citations.push({
        document_id: "medication-list",
        document_title: "Medication list (recorded in demo chart)",
        section: "Current medications",
        snippet: `${m.name} ${m.dosage}, ${m.frequency}, started ${m.started}`,
      });
      if (match.drug.test("warfarin|metronidazole|maoi|phenelzine")) safety = "needs_clinician_review";
    }
  }

  if (findings.length === 0) {
    findings.push(
      `No specific food–medicine interaction is recorded between your current medications (${meds
        .map((m) => m.name)
        .join(", ")}) and the foods you asked about.`,
    );
    citations.push({
      document_id: "medication-list",
      document_title: "Medication list (recorded in demo chart)",
      section: "Current medications",
      snippet: meds.map((m) => `${m.name} ${m.dosage}`).join("; "),
    });
  }

  if (patient.dietary_restrictions.length > 0) {
    findings.push(`Also recorded for you: ${patient.dietary_restrictions.join("; ")}.`);
  }

  const weightLoss = weightLossPercent(patientId);
  const appetiteNote: Record<string, string> = {
    good: "Your appetite is recorded as good.",
    reduced: "Your records note a reduced appetite — smaller, more frequent meals is a commonly suggested strategy your dietitian can tailor.",
    poor: "Your records note a poor appetite and meaningful weight loss — this is exactly what your dietitian referral is addressing; new eating plans should be confirmed with them.",
  };
  findings.push(appetiteNote[patient.appetite]);

  if (patient.appetite === "poor" || (weightLoss !== null && weightLoss >= 5)) {
    safety = "needs_clinician_review";
  }

  return {
    question,
    summary:
      `Every food suggestion is checked against your recorded medications before it is shown. ` +
      findings.join(" "),
    key_findings: findings,
    citations,
    missing_info: [
      "Your dietitian's current meal plan (not transcribed into the demo record).",
      "Recent changes to your medication list made outside the demo period.",
    ],
    safety,
    safety_note: SAFETY_EXPLAIN[safety],
    generator: "template-v1",
    plain_terms: findTermExplanations(findings.join(" ")),
  };
}

// ------------------------------------------------- appointment preparation
export function appointmentPrep(patientId: string): {
  appointment: ReturnType<typeof getAppointment>;
  suggested_questions: string[];
  bring_with_you: string[];
  citations: Citation[];
  safety: SafetyCategory;
} {
  const patient = getPatient(patientId);
  const appt = getAppointment(patientId);
  const labs = getLabs(patientId);
  const questions: string[] = [];
  const bring: string[] = ["Your medication list (or the bottles)", "Questions you write down beforehand"];

  if (patient && labs.length > 0) {
    const latest = labs[labs.length - 1];
    if (latest.albumin_g_dl < 3.5) {
      questions.push(
        `My last albumin was ${latest.albumin_g_dl} g/dL, below the usual reference range. Does this change my nutrition plan?`,
      );
      bring.push("Any dietitian notes you have received");
    }
    if (latest.hemoglobin_g_dl < 12) {
      questions.push(
        `My haemoglobin was ${latest.hemoglobin_g_dl} g/dL. Is this related to treatment, and should it be monitored more often?`,
      );
    }
  }

  if (patient) {
    if (/neuropathy|tingling/i.test(JSON.stringify(patient.history_events))) {
      questions.push("The tingling in my hands when touching cold things is affecting daily life. What are the options?");
    }
    if (patient.appetite === "poor" || patient.appetite === "reduced") {
      questions.push("My appetite and weight have changed since treatment started. What should we watch for?");
    }
    if (patient.medications.some((m) => /letrozole|tamoxifen/i.test(m.name))) {
      questions.push("Are the side effects I'm having from this hormone tablet expected at this dose?");
    }
    questions.push("What symptoms should make me call the team between visits, rather than waiting for the next appointment?");
  }

  const citations: Citation[] = [];
  if (patient) {
    for (const ev of patient.history_events.slice(-2)) {
      citations.push({
        document_id: "visit-history",
        document_title: "Documented history timeline",
        section: ev.date,
        snippet: `${ev.event}: ${ev.detail}`,
      });
    }
  }

  return {
    appointment: appt,
    suggested_questions: questions.slice(0, 6),
    bring_with_you: bring,
    citations,
    safety: "needs_clinician_review",
  };
}

// ------------------------------------------------------- patient brief
export interface PatientBrief {
  overview: string;
  recent_labs: string[];
  nutrition_status: string;
  missing_information: string[];
  draft_label: string;
  citations: Citation[];
}

export function patientBrief(patientId: string): PatientBrief | null {
  const p = getPatient(patientId);
  if (!p) return null;
  const labs = getLabs(patientId);
  const wl = weightLossPercent(patientId);
  const latest = labs[labs.length - 1];

  const recent_labs = labs
    .slice(-2)
    .map(
      (l) =>
        `${l.date}: albumin ${l.albumin_g_dl} g/dL, haemoglobin ${l.hemoglobin_g_dl} g/dL, creatinine ${l.creatinine_mg_dl} mg/dL, CRP ${l.crp_mg_l} mg/L`,
    );

  const nutritionBits: string[] = [];
  if (wl !== null) nutritionBits.push(`weight change ${wl > 0 ? "-" : "+"}${Math.abs(wl)}% since first recording`);
  if (latest && latest.albumin_g_dl < 3.5) nutritionBits.push(`albumin ${latest.albumin_g_dl} g/dL (low)`);
  nutritionBits.push(`appetite documented as ${p.appetite}`);

  const missing_information: string[] = [];
  if (!latest) missing_information.push("No lab results in the demo record.");
  else {
    if (latest.albumin_g_dl >= 3.5 && wl !== null && wl < 5) missing_information.push("No active nutrition red flags — but no recent formal dietitian assessment is on file either.");
    missing_information.push("Weight measurements are recorded at only two time points.");
  }
  missing_information.push("Patient-reported symptoms between visits are not in the demo record.");

  return {
    overview: `${p.name}, ${p.age} ${p.sex[0].toLowerCase()}. ${p.diagnosis_details}`,
    recent_labs,
    nutrition_status: nutritionBits.join("; ") + ".",
    missing_information,
    draft_label: "AI DRAFT — not applied to the record until a clinician approves it",
    citations: getDocuments(patientId)
      .slice(0, 2)
      .flatMap((d) => d.sections.slice(0, 1).map((s) => ({
        document_id: d.id,
        document_title: d.title,
        section: s.heading,
        snippet: s.text.slice(0, 200),
      }))),
  };
}

// ---------------------------------------------------- risk watcher (silent)
export interface RiskAssessment {
  silent: boolean;
  alert: null | {
    level: "watch" | "high";
    reasons: string[];
    suggestion: string;
  };
}

export function riskAssessment(patientId: string): RiskAssessment {
  const p = getPatient(patientId);
  const labs = getLabs(patientId);
  const latest = labs[labs.length - 1];
  const wl = weightLossPercent(patientId);
  const reasons: string[] = [];

  if (wl !== null && wl >= 10) reasons.push(`Documented weight loss ${wl}% (threshold: ≥10% in 6 months)`);
  else if (wl !== null && wl >= 5) reasons.push(`Documented weight loss ${wl}% (threshold: ≥5% in 6 months)`);
  if (latest && latest.albumin_g_dl < 3.5) reasons.push(`Albumin ${latest.albumin_g_dl} g/dL (threshold: <3.5 g/dL)`);
  if (p && p.appetite === "poor") reasons.push("Appetite documented as poor");

  if (reasons.length === 0) {
    return { silent: true, alert: null };
  }

  return {
    silent: false,
    alert: {
      level: reasons.length >= 2 ? "high" : "watch",
      reasons,
      suggestion: "Suggest dietitian referral for formal nutrition assessment.",
    },
  };
}
