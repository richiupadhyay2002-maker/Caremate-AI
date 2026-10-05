// API client for Caremate AI backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

// ---- Auth ----
export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: number;
  email: string;
  full_name: string;
  role: string;
  patient_id?: number;
  doctor_id?: number;
}

export interface TokenInfo {
  sub: string;
  role: string;
  email: string;
  patient_id?: number;
  doctor_id?: number;
}

// ---- Patient models (from backend PatientContext) ----
export interface MedicationEntry {
  name: string;
  dosage: string;
  frequency: string;
  started_date?: string;
  notes?: string;
}

export interface AllergyEntry {
  substance: string;
  reaction: string;
  severity: string;
}

export interface PatientContext {
  patient_id: string;
  name: string;
  age?: number;
  sex?: string;
  medical_history?: string[];
  current_medications?: MedicationEntry[];
  allergies?: AllergyEntry[];
  dietary_restrictions?: string[];
  recent_weight?: number;
  height?: number;
  lab_results?: Record<string, number>;
  notes?: string;
}

// ---- Documents ----
export interface DocumentRef {
  document_id: string;
  title: string;
  document_type: string;
  source: string;
  created_at?: string;
}

export interface ChunkRef {
  chunk_id: string;
  document_id: string;
  section: string;
  content: string;
  token_count: number;
}

// ---- Ask / AI ----
export interface Citation {
  source_document: string;
  section: string;
  chunk_id: string;
  page_number?: number;
  relevance_score: number;
  text_snippet: string;
}

export interface StructuredAIResponse {
  response: string;
  citations: Citation[];
  confidence: number;
  safety_flags: string[];
  metadata: Record<string, unknown>;
}

// ---- Doctor generations ----
export interface GenerationSummary {
  id: number;
  patient_id: string;
  patient_name?: string;
  query: string;
  response_text: string;
  confidence: number;
  safety_flags: string[];
  status: string;
  created_at?: string;
  reviewed_at?: string;
  review_status: string;
    citation_count: number;
  doctor_notes?: string;
  full_response_json?: Record<string, unknown>;
}

export interface GenerationCitation {
  chunk_id: string;
  source_document: string;
  section: string;
  page_number?: number;
  relevance_score: number;
  text_snippet: string;
}

export interface GenerationDetail {
  id: number;
  patient_id: string;
  patient_name?: string;
  query: string;
  response_text: string;
  confidence: number;
  safety_flags: string[];
  status: string;
  created_at?: string;
  reviewed_at?: string;
  review_status: string;
  citation_count: number;
  full_response_json: Record<string, unknown>;
  citations: GenerationCitation[];
  doctor_notes?: string;
  metadata: Record<string, unknown>;
}

// ---- Ask ----
export interface AskRequest {
  query: string;
  raw_documents?: string[];
}

// ---- Doctor patients ----
export interface DoctorPatientSummary {
  patient_id: string;
  full_name?: string;
  age?: number;
  sex?: string;
  medical_history?: string[];
  allergies?: AllergyEntry[];
  recent_weight?: number;
  last_activity?: string;
}

// ---- Auth: register / password reset / profile ----
export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  role?: string;
}

export async function register(
  email: string,
  password: string,
  full_name: string
): Promise<UserResponse> {
  return apiRequest<UserResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name, role: "patient" }),
  });
}

export async function forgotPassword(
  email: string
): Promise<{ message: string; reset_token: string | null }> {
  return apiRequest("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function resetPassword(
  token: string,
  new_password: string
): Promise<{ message: string }> {
  return apiRequest("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, new_password }),
  });
}

export async function updateProfile(
  full_name: string
): Promise<UserResponse> {
  return apiRequest<UserResponse>("/auth/me", {
    method: "PATCH",
    body: JSON.stringify({ full_name }),
  });
}

export async function getMyPatientRecord(): Promise<{
  patient_id: string;
  full_name: string;
}> {
  return apiRequest("/auth/me/patient-record");
}

// ---- Demo / sample files ----
export interface SampleFile {
  sample_id: string;
  filename: string;
  title: string;
  kind: string;
  size_bytes: number;
  excerpt: string;
}

export interface SampleListResponse {
  samples: SampleFile[];
  notice: string;
  sources_note: string;
}

export async function listDemoSamples(): Promise<SampleListResponse> {
  return apiRequest<SampleListResponse>("/demo/samples");
}

export async function processDemoSample(
  sampleId: string,
  query?: string
): Promise<StructuredAIResponse> {
  return apiRequest<StructuredAIResponse>("/demo/process", {
    method: "POST",
    body: JSON.stringify({ sample_id: sampleId, query }),
  });
}

// ---- Uploads (multipart) ----
export interface UploadResult {
  document_id: string;
  num_chunks: number;
  pages_extracted: number;
  ocr_used: boolean;
  document_type: string;
  classification_confidence: number;
}

export async function uploadDocument(
  patientId: string,
  file: File,
  onProgress?: (pct: number) => void
): Promise<UploadResult> {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("caremate_token")
      : null;
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(
    `${API_BASE}/patients/${patientId}/documents/upload`,
    {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    }
  );
  if (!response.ok) {
    let detail = "Upload failed.";
    try {
      const err = await response.json();
      detail = err.detail || JSON.stringify(err);
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }
  onProgress?.(100);
  return response.json() as Promise<UploadResult>;
}

export async function deleteDocument(
  patientId: string,
  documentId: string
): Promise<{ deleted: string; files_removed: number }> {
  return apiRequest(
    `/patients/${patientId}/documents/${documentId}`,
    { method: "DELETE" }
  );
}

export interface MyGeneration {
  id: number;
  query: string;
  response_text: string;
  confidence: number | null;
  safety_flags: string[];
  created_at: string | null;
}

export async function listMyGenerations(
  patientId: string
): Promise<MyGeneration[]> {
  return apiRequest<MyGeneration[]>(
    `/patients/${patientId}/generations`
  );
}

// ---- Core API request ----
export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("caremate_token")
      : null;
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    let errorDetail = "";
    try {
      const err = await response.json();
      errorDetail = JSON.stringify(err);
    } catch {
      errorDetail = response.statusText;
    }
    throw new Error(`API error ${response.status}: ${errorDetail}`);
  }
    return response.json() as Promise<T>;
}

// ---- Auth functions ----
export async function login(
  email: string,
  password: string
): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/auth/token", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getMe(): Promise<UserResponse> {
  return apiRequest<UserResponse>("/auth/me");
}

export async function getTokenInfo(): Promise<TokenInfo> {
  return apiRequest<TokenInfo>("/auth/me/token-info");
}

// ---- Patient functions ----
export async function getPatientContext(
  patientId: string
): Promise<PatientContext> {
  return apiRequest<PatientContext>(`/patients/${patientId}/context`);
}

export async function listDocuments(patientId: string): Promise<DocumentRef[]> {
  return apiRequest<DocumentRef[]>(`/patients/${patientId}/documents`);
}

export async function getSignedUrl(
  patientId: string,
  documentId: string
): Promise<{ url: string; expires_at: string }> {
  return apiRequest<{ url: string; expires_at: string }>(
    `/patients/${patientId}/documents/${documentId}/signed-url`
  );
}

export async function askQuestion(
  patientId: string,
  question: string
): Promise<StructuredAIResponse> {
  return apiRequest<StructuredAIResponse>(`/patients/${patientId}/ask`, {
    method: "POST",
    body: JSON.stringify({ query: question }),
  });
}

export async function fetchDocumentChunks(
  patientId: string,
  documentId: string
): Promise<ChunkRef[]> {
  return apiRequest<ChunkRef[]>(
    `/patients/${patientId}/documents/${documentId}/chunks`
  );
}

export async function deletePatient(patientId: string): Promise<void> {
  await apiRequest(`/patients/${patientId}`, { method: "DELETE" });
}

// ---- Doctor functions ----
export async function listDoctorPatients(): Promise<DoctorPatientSummary[]> {
  return apiRequest<DoctorPatientSummary[]>("/doctors/me/patients");
}

export async function listPatientGenerations(
  patientId: string
): Promise<GenerationSummary[]> {
  return apiRequest<GenerationSummary[]>(
    `/doctors/me/patients/${patientId}/generations`
  );
}

export async function getGenerationDetail(
  generationId: number
): Promise<GenerationDetail> {
  return apiRequest<GenerationDetail>(
    `/doctors/me/generations/${generationId}`
  );
}

export async function reviewGeneration(
  generationId: number,
  status: string,
  doctor_notes?: string,
  edited_response?: string
): Promise<GenerationDetail> {
  return apiRequest<GenerationDetail>(
    `/doctors/me/generations/${generationId}`,
    {
      method: "PATCH",
      body: JSON.stringify({ status, doctor_notes, edited_response }),
    }
  );
}

export const API_BASE_URL = API_BASE;