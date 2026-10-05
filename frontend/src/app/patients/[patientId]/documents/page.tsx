"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { listDocuments, DocumentRef, getSignedUrl } from "@/lib/api";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function PatientDocumentsPage() {
  const params = useParams() as { patientId: string };
  const { token } = useAuth();
  const [documents, setDocuments] = useState<DocumentRef[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    const fetchDocs = async () => {
      try {
        setLoading(true);
        const docs = await listDocuments(params.patientId);
        setDocuments(docs);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    };
    fetchDocs();
  }, [params.patientId, token]);

  if (!token) return <p className="py-8">Please <a href="/login" className="text-primary">log in</a>.</p>;
  if (loading) return <p className="py-8">Loading documents...</p>;
  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div className="space-y-4">
      <Link href={`/patients/${params.patientId}`}>
        <span className="text-primary hover:underline cursor-pointer">← Back to patient</span>
      </Link>
      <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
      <div className="grid gap-3">
        {documents.map((doc) => (
          <Link
            key={doc.document_id}
            href={`/patients/${params.patientId}/documents/${doc.document_id}/chunks`}
          >
            <div className="bg-white border border-gray-200 rounded-lg p-4 hover:bg-gray-50 cursor-pointer">
              <h3 className="font-medium text-gray-900">{doc.title}</h3>
              <p className="text-sm text-gray-600">
                {doc.document_type} • {doc.source}
              </p>
                            <p className="text-xs text-gray-400">
                Created: {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : "N/A"}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}