"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { type ChunkRef, type DocumentRef, getSignedUrl, listDocuments, fetchDocumentChunks } from "@/lib/api";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function DocumentChunksPage() {
  const params = useParams() as { patientId: string; documentId: string };
  const { token } = useAuth();
  const [chunks, setChunks] = useState<ChunkRef[]>([]);
  const [docInfo, setDocInfo] = useState<DocumentRef | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    const fetchData = async () => {
      try {
        setLoading(true);
        const docs = await listDocuments(params.patientId);
        const doc = docs.find((d) => d.document_id === params.documentId);
        setDocInfo(doc || null);

        const chunksData = await fetchDocumentChunks(
          params.patientId,
          params.documentId
        );
        setChunks(chunksData);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [params.patientId, params.documentId, token]);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const { url } = await getSignedUrl(params.patientId, params.documentId);
      window.open(url, "_blank");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to get URL");
    } finally {
      setDownloading(false);
    }
  };

  if (!token) return <p className="py-8">Please <a href="/login" className="text-blue-600">log in</a>.</p>;
  if (loading) return <p className="py-8">Loading chunks...</p>;
  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div className="space-y-4">
      <Link href={`/patients/${params.patientId}/documents`}>
        <span className="text-blue-600 hover:underline cursor-pointer">Back to documents</span>
      </Link>

      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {docInfo?.title || params.documentId}
          </h1>
          <p className="text-sm text-gray-600">
            {docInfo?.document_type} - {docInfo?.source}
          </p>
        </div>
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
        >
          {downloading ? "Generating..." : "Download (Signed URL)"}
        </button>
      </div>

      <div className="space-y-3">
        {chunks.map((chunk) => (
          <div
            key={chunk.chunk_id}
            className="bg-white border border-gray-200 rounded-lg p-4"
          >
            <div className="flex justify-between items-start mb-2">
              <div className="flex gap-4 text-xs text-gray-500">
                {chunk.section && (
                  <span className="px-2 py-1 bg-gray-100 rounded">
                    Section: {chunk.section}
                  </span>
                )}
                <span>Tokens: {chunk.token_count}</span>
              </div>
            </div>
            <p className="text-gray-800 text-sm leading-relaxed">
              {chunk.content}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}