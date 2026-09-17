"""Isolated database fixtures for manual evals, built through actual extraction/chunking.

These are newly generated evaluation PDFs containing attributed factual paraphrases.
They are not the manufacturer's original PDF and are never saved to account storage.
"""

import hashlib
from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import uuid4

import pymupdf
from app.db import engine
from app.documents.chunking import CHUNKING_VERSION, PageSource, build_chunks
from app.documents.extraction import extract_page
from app.models.attachment import Attachment
from app.models.bike import Bike
from app.models.document import Document
from app.models.document_index import DocumentIndex
from app.models.document_ingestion import DocumentIngestion
from app.models.user import User
from app.services.document_ingestion import PIPELINE_VERSION
from sqlalchemy.orm import Session

from vroometr.ai.embeddings import validate_vectors


def pdf_bytes(pages):
    with pymupdf.open() as pdf:
        for entry in pages:
            page = pdf.new_page()
            if entry["state"] == "pending_provider":
                for index in range(12):
                    page.draw_rect(pymupdf.Rect(30 + index * 8, 40, 36 + index * 8, 90))
            else:
                remaining = page.insert_textbox(
                    pymupdf.Rect(30, 30, 550, 780),
                    entry["title"] + "\n" + entry["text"],
                    fontsize=11,
                )
                if remaining < 0:
                    raise ValueError("Fixture text overflow")
        pdf.set_toc([[1, entry["title"], index + 1] for index, entry in enumerate(pages)])
        return pdf.tobytes()


@contextmanager
def corpus(dataset, embedder, model, version):
    # No pytest skip fallback: missing DB/migration is an eval error, never a passing gate.
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with Session(bind=connection) as session:
                user = User(clerk_user_id=f"eval-{uuid4()}")
                session.add(user)
                session.flush()
                bikes = []
                for label in ("manual", "visual_only"):
                    bike = Bike(
                        user_id=user.id,
                        nickname=f"Eval {label}",
                        make="Honda",
                        model="CRF250F",
                        year=2021,
                        bike_type="dirt_bike",
                        powertrain_type="combustion",
                        displacement=250,
                        stroke_type="4T",
                    )
                    session.add(bike)
                    bikes.append(bike)
                session.flush()
                mapping, originals, pending = {}, {}, []
                groups = [
                    ([p for p in dataset["pages"] if not p.get("supporting")], bikes[0], False),
                    ([p for p in dataset["pages"] if p.get("supporting")], bikes[0], True),
                    (
                        [p for p in dataset["pages"] if p["state"] == "pending_provider"],
                        bikes[1],
                        False,
                    ),
                ]
                for entries, bike, supporting in groups:
                    data = pdf_bytes(entries)
                    source_hash = hashlib.sha256(data).hexdigest()
                    file = Attachment(
                        user_id=user.id,
                        s3_key=f"eval-only/{uuid4()}",
                        file_name="evaluation-paraphrases.pdf",
                        mime_type="application/pdf",
                        file_size=len(data),
                        status="uploaded",
                        purpose="document",
                        retention_class="persistent",
                    )
                    session.add(file)
                    session.flush()
                    doc = Document(
                        bike_id=bike.id,
                        attachment_id=file.id,
                        document_type="supporting_document"
                        if supporting
                        else "manufacturer_manual",
                        make="Honda",
                        model="CRF250F",
                        year=2021,
                        file_hash=source_hash,
                        status="active",
                        is_primary=not supporting,
                        confirmed_at=datetime.now(UTC),
                    )
                    session.add(doc)
                    session.flush()
                    attempt = uuid4()
                    with pymupdf.open(stream=data, filetype="pdf") as pdf:
                        pages = [
                            extract_page(pdf, index, doc.id, source_hash)
                            for index in range(len(entries))
                        ]
                        for entry, page in zip(entries, pages, strict=True):
                            if page.state != entry["state"]:
                                raise AssertionError(f"Routing changed for fixture {entry['id']}")
                            mapping[(doc.id, page.page_index)] = entry["id"]
                            originals[(doc.id, page.page_index)] = page
                            if page.state != "completed":
                                pending.append((doc.id, page.page_index))
                        plan = build_chunks(
                            doc.id,
                            [
                                PageSource(
                                    p.page_index,
                                    p.text,
                                    p.source_hash,
                                    p.extraction_version,
                                    p.state,
                                )
                                for p in pages
                            ],
                            pdf.get_toc(),
                        )
                    state = "partial" if any(p.state != "completed" for p in pages) else "completed"
                    session.add(
                        DocumentIngestion(
                            document_id=doc.id,
                            attempt_id=attempt,
                            state=state,
                            pipeline_version=PIPELINE_VERSION,
                            page_count=len(pages),
                            updated_at=datetime.now(UTC),
                        )
                    )
                    session.add_all(pages)
                    session.add(
                        DocumentIndex(
                            document_id=doc.id,
                            attempt_id=uuid4(),
                            source_attempt_id=attempt,
                            state=state,
                            chunking_version=CHUNKING_VERSION,
                            embedding_model=model,
                            embedding_version=version,
                            updated_at=datetime.now(UTC),
                        )
                    )
                    session.add_all(plan.sections)
                    session.flush()
                    for start in range(0, len(plan.chunks), 16):
                        batch = plan.chunks[start : start + 16]
                        vectors = validate_vectors(
                            embedder.embed([c.cleaned_text for c in batch]), len(batch)
                        )
                        for chunk, vector in zip(batch, vectors, strict=True):
                            chunk.embedding, chunk.embedding_model, chunk.embedding_version = (
                                vector,
                                model,
                                version,
                            )
                    session.add_all(plan.chunks)
                    session.flush()
                yield (
                    session,
                    user.id,
                    {label: bike.id for label, bike in zip(("manual", "visual_only"), bikes)},
                    mapping,
                    originals,
                    pending,
                )
        finally:
            transaction.rollback()
