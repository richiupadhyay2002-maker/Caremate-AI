"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  getPatientContext,
  listDocuments,
  PatientContext,
  DocumentRef,
} from "@/lib/api";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function PatientDetailPage() {
  const params = useParams() as { patientId: string };
  const { token } = useAuth();
  const [context, setContext] = useState<PatientContext | null>(null);
  const [documents, setDocuments] = useState<DocumentRef[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    const fetchData = async () => {
      try {
        setLoading(true);
        const ctx = await getPatientContext(params.patientId);
        setContext(ctx);
        const docs = await listDocuments(params.patientId);
        setDocuments(docs);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [params.patientId, token]);

  if (!token) {
    return (
      <div className="text-center py-8 text-gray-500">
        Please <a href="/login" className="text-primary underline">log in</a>.
      </div>
    );
  }

  if (loading) return <div className="text-center py-8">Loading...</div>;
  if (error)
    return (
      <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
        {error}
      </div>
    );

  return (
    <div className="space-y-6">
      {context && (
        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
                    <h1 className="text-2xl font-bold text-gray-900">
              {context.name}
          </h1>
          <div className="grid md:grid-cols-4 gap-4 mt-4 text-sm">
            <div>
              <span className="text-gray-500">Patient ID:</span>{" "}
              <strong>{context.patient_id}</strong>
            </div>
            <div>
              <span className="text-gray-500">Age:</span>{" "}
              <strong>{context.age}</strong>
            </div>
            <div>
              <span className="text-gray-500">Sex:</span>{" "}
              <strong>{context.sex}</strong>
            </div>
          </div>

          {context.current_medications && context.current_medications.length > 0 && (
            <div className="mt-4">
              <h3 className="font-medium text-gray-700 mb-2">Medications</h3>
              <div className="flex flex-wrap gap-2">
                {context.current_medications.map((med, i) => (
                  <span key={i} className="px-3 py-1 bg-blue-50 text-blue-800 rounded text-sm">
                    {med.name} - {med.dosage} ({med.frequency})
                  </span>
                ))}
              </div>
            </div>
          )}

          {context.allergies && context.allergies.length > 0 && (
            <div className="mt-4">
              <h3 className="font-medium text-gray-700 mb-2">Allergies</h3>
              <div className="flex flex-wrap gap-2">
                {context.allergies.map((a, i) => (
                  <span key={i} className="px-3 py-1 bg-red-100 text-red-800 rounded text-sm">
                    {a.substance} ({a.severity})
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Documents */}
      <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Medical Documents
        </h2>
        {documents.length === 0 ? (
          <p className="text-gray-500 text-sm">No documents found.</p>
        ) : (
          <div className="grid gap-3">
            {documents.map((doc) => (
              <Link
                key={doc.document_id}
                href={`/patients/${params.patientId}/documents/${doc.document_id}/chunks`}
              >
                <div className="border border-gray-200 rounded-lg p-3 hover:bg-gray-50 cursor-pointer transition">
                  <div className="font-medium text-gray-900">
                    {doc.title}
                  </div>
                  <div className="text-sm text-gray-600">
                    {doc.document_type} • {doc.source}
                  </div>
                                    <div className="text-xs text-gray-400">
                    {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : "N/A"}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
