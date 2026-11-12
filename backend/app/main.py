"""TriaseKu API (MVP demo).

PERINGATAN: penyimpanan masih in-memory dan login masih versi demo.
Untuk produksi: ganti ke PostgreSQL, enkripsi kolom sensitif, OTP/JWT.
Gunakan data sintetis saja.
"""
import secrets
import time
import uuid
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from . import triage

app = FastAPI(title="TriaseKu API", version="0.1.0")

USERS: dict[str, dict] = {}       # token -> user
CONSENTS: dict[str, bool] = {}    # user_id -> granted
SESSIONS: dict[str, dict] = {}
AUDIT: list[dict] = []


def audit(actor: str, action: str, obj: str) -> None:
    AUDIT.append({"actor": actor, "action": action, "object": obj, "at": time.time()})


def current_user(authorization: str = Header(default="")) -> dict:
    user = USERS.get(authorization.removeprefix("Bearer ").strip())
    if not user:
        raise HTTPException(401, "Token tidak valid")
    return user


def need(*roles: str):
    def dep(user: dict = Depends(current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(403, "Peran tidak diizinkan")
        return user
    return dep


def own_session(sid: str, user: dict) -> dict:
    s = SESSIONS.get(sid)
    if not s or s["patient_id"] != user["id"]:
        raise HTTPException(404, "Sesi tidak ditemukan")
    return s


class LoginIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    role: Literal["pasien", "dokter", "admin"] = "pasien"


class ConsentIn(BaseModel):
    granted: bool


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class VerifyIn(BaseModel):
    catatan: str | None = Field(default=None, max_length=500)
    arahan: Literal["DARURAT", "KONSULTASI", "MANDIRI"] | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/login")
def login(body: LoginIn):
    """Login demo tanpa kata sandi/OTP. Ganti dengan OTP + JWT untuk produksi."""
    user = {"id": str(uuid.uuid4()), "name": body.name, "role": body.role}
    token = secrets.token_urlsafe(24)
    USERS[token] = user
    audit(user["id"], "login", user["role"])
    return {"token": token, "user": user}


@app.post("/consents")
def set_consent(body: ConsentIn, user: dict = Depends(need("pasien"))):
    CONSENTS[user["id"]] = body.granted
    audit(user["id"], "consent_granted" if body.granted else "consent_revoked", "consent")
    return {"granted": body.granted}


@app.post("/intake/sessions")
def start_session(user: dict = Depends(need("pasien"))):
    if not CONSENTS.get(user["id"]):
        raise HTTPException(403, "Persetujuan (consent) diperlukan")
    sid = str(uuid.uuid4())
    SESSIONS[sid] = {
        "id": sid, "patient_id": user["id"], "step": 0, "answers": {},
        "messages": [], "red_flags": [], "done": False, "shared": False, "result": None,
    }
    audit(user["id"], "intake_start", sid)
    return {"session_id": sid, "question": triage.next_question(0)}


@app.post("/intake/sessions/{sid}/messages")
def send_message(sid: str, body: MessageIn, user: dict = Depends(need("pasien"))):
    s = own_session(sid, user)
    if not CONSENTS.get(user["id"]):
        raise HTTPException(403, "Persetujuan (consent) telah dicabut")
    if s["done"]:
        raise HTTPException(409, "Sesi sudah selesai")

    text = body.text.strip()
    s["messages"].append({"from": "pasien", "text": text})
    s["red_flags"] += triage.find_red_flags(text)
    s["answers"][triage.QUESTIONS[s["step"]][0]] = text
    s["step"] += 1

    if s["red_flags"] or s["step"] >= len(triage.QUESTIONS):
        hasil = triage.decide(s["answers"], s["red_flags"])
        summary = triage.build_summary(s["answers"], hasil)
        s["result"] = {**hasil, "summary": summary}
        s["done"] = True
        audit(user["id"], "intake_done", sid)
        return {"done": True, "question": None, "result": s["result"]}

    question = triage.next_question(s["step"])
    s["messages"].append({"from": "ai", "text": question})
    return {"done": False, "question": question, "result": None}


@app.get("/intake/sessions/{sid}/result")
def get_result(sid: str, user: dict = Depends(need("pasien"))):
    s = own_session(sid, user)
    if not s["done"]:
        raise HTTPException(409, "Sesi belum selesai")
    return s["result"]


@app.post("/intake/sessions/{sid}/share")
def share(sid: str, user: dict = Depends(need("pasien"))):
    s = own_session(sid, user)
    if not s["done"]:
        raise HTTPException(409, "Sesi belum selesai")
    s["shared"] = True
    audit(user["id"], "share_to_doctor", sid)
    return {"shared": True}


@app.delete("/intake/sessions/{sid}")
def delete_session(sid: str, user: dict = Depends(need("pasien"))):
    own_session(sid, user)
    del SESSIONS[sid]
    audit(user["id"], "delete_session", sid)
    return {"deleted": True}


@app.get("/summaries")
def list_pending(user: dict = Depends(need("dokter"))):
    audit(user["id"], "list_summaries", "pending")
    return [
        {"session_id": s["id"], **s["result"]["summary"]}
        for s in SESSIONS.values()
        if s["done"] and s["shared"] and s["result"]["summary"]["status"] == "Belum Diverifikasi"
    ]


@app.patch("/summaries/{sid}/verify")
def verify(sid: str, body: VerifyIn, user: dict = Depends(need("dokter"))):
    s = SESSIONS.get(sid)
    if not s or not s["done"] or not s["shared"]:
        raise HTTPException(404, "Ringkasan tidak ditemukan atau belum dibagikan")
    summary = s["result"]["summary"]
    summary.update(status="Terverifikasi", dokter_id=user["id"], catatan_dokter=body.catatan)
    if body.arahan:
        s["result"]["arahan"] = body.arahan
    audit(user["id"], "verify_summary", sid)
    return s["result"]


@app.get("/admin/audit-logs")
def audit_logs(user: dict = Depends(need("admin"))):
    return AUDIT
