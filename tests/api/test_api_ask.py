"""API tests for document ingestion and ask/nutrition endpoints."""

from __future__ import annotations


def _ingest(client, headers, patient_id, text, dtype="clinical_note"):
    return client.post(
        f"/patients/{patient_id}/documents",
        json={"text": text, "document_type": dtype},
        headers=headers,
    )


def test_ask_returns_structured_response(client, patient_token, db):
    """A logged-in patient can hit /patients/{id}/ask and get a StructuredAIResponse."""
    doc_text = (
        "PATIENT HISTORY\n"
        "65-year-old male with heart failure and hypertension.\n"
        "MEDICATIONS\n"
        "- Lisinopril 10mg daily (ACE inhibitor)\n"
        "- Warfarin 5mg daily (monitor INR weekly)\n"
        "LABORATORY RESULTS\n"
        "- Albumin: 3.4 g/dL\n"
    )
    r = _ingest(client, patient_token, "api_patient_1", doc_text)
    assert r.status_code == 200, r.text
    assert r.json()["num_chunks"] > 0

    r = client.post("/patients/api_patient_1/ask",
                    json={"query": "What medications is the patient taking?"},
                    headers=patient_token)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "response" in data
    assert isinstance(data["response"], str) and len(data["response"]) > 0
    assert isinstance(data.get("citations"), list)
    assert 0.0 <= data.get("confidence", 0) <= 1.0

    # Verify the pipeline actually retrieved chunks from the DB-backed
    # vector store — the mock LLM may not echo exact terms, but the retrieval
    # must have hit the persistent store.
    from caremate.db.models_patients import Patient as OrmPatient
    from caremate.db.models_docs import DocumentChunk as OrmChunk
    patient = db.query(OrmPatient).filter(OrmPatient.patient_id == "api_patient_1").first()
    chunks = db.query(OrmChunk).filter(OrmChunk.patient_id == patient.id).all()
    assert len(chunks) > 0, "Document chunks should be persisted in the DB"
    assert any("lisinopril" in c.content.lower() for c in chunks), "Chunks should contain lisinopril"


def test_ask_persists_generation_to_db(client, patient_token, db):
    """The AI generation is persisted in the database."""
    doc = "MEDICATIONS\n- Metformin 500mg twice daily\n- Atorvastatin 20mg nightly\n"
    _ingest(client, patient_token, "api_patient_1", doc)
    client.post("/patients/api_patient_1/ask",
                json={"query": "what medications is the patient on?"},
                headers=patient_token)

    from caremate.db.models_comm import AI_Generation as OrmGen
    from caremate.db.models_patients import Patient as OrmPatient
    patient = db.query(OrmPatient).filter(OrmPatient.patient_id == "api_patient_1").first()
    gens = db.query(OrmGen).filter(OrmGen.patient_id == patient.id).all()
    assert len(gens) >= 1
    assert "what medications" in gens[-1].query.lower()


def test_ask_with_raw_documents(client, patient_token):
    """Passing raw_documents in the ask payload works without prior ingestion."""
    r = client.post("/patients/api_patient_1/ask",
                    json={
                        "query": "What should I avoid?",
                        "raw_documents": ["CRANBERRY JUICE INTERFERES WITH WARFARIN.\nAVOID CRANBERRY PRODUCTS."],
                    },
                    headers=patient_token)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "response" in data


def test_nutrition_ask_endpoint(client, patient_token):
    """The /ask/nutrition endpoint works and returns a structured response."""
    doc = (
        "NUTRITIONAL ASSESSMENT\n"
        "Patient shows signs of malnutrition risk.\n"
        "DIETARY INSTRUCTIONS\n"
        "- Limit sodium to less than 2000mg per day\n"
    )
    _ingest(client, patient_token, "api_patient_1", doc)
    r = client.post("/patients/api_patient_1/ask/nutrition",
                    json={"query": "Any dietary recommendations?"},
                    headers=patient_token)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "response" in data
