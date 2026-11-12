"""Logika triase TriaseKu.

Aturan tanda bahaya bersifat deterministik dan SELALU dijalankan.
Titik sambung LLM: ganti `next_question` dengan pemanggilan adapter LLM
(data sudah dianonimkan), tetapi `find_red_flags` dan `decide` tetap
berfungsi sebagai pagar pengaman. AI hanya mengarahkan, bukan mendiagnosis.
"""
import re

DARURAT, KONSULTASI, MANDIRI = "DARURAT", "KONSULTASI", "MANDIRI"

RED_FLAGS = (
    "nyeri dada", "sesak napas berat", "sesak berat", "sulit bernapas",
    "tidak bisa bernapas", "pingsan", "tidak sadar", "kejang",
    "perdarahan hebat", "muntah darah", "batuk darah", "lumpuh",
    "wajah miring", "bicara pelo", "bunuh diri",
)

QUESTIONS = (
    ("keluhan", "Apa keluhan utama Anda?"),
    ("durasi", "Sudah berapa lama? (contoh: 3 hari)"),
    ("keparahan", "Seberapa berat dari 1 sampai 10?"),
    ("riwayat", "Apakah ada riwayat penyakit? (tulis 'tidak ada' bila tidak)"),
    ("obat", "Obat apa yang sedang diminum?"),
    ("alergi", "Apakah ada alergi?"),
)


def next_question(step: int) -> str:
    return QUESTIONS[step][1]


def find_red_flags(text: str) -> list[str]:
    t = text.lower()
    return [f for f in RED_FLAGS if f in t]


def parse_severity(text: str) -> int | None:
    m = re.search(r"\b(10|[1-9])\b", text)
    return int(m.group(1)) if m else None


def parse_days(text: str) -> int | None:
    m = re.search(r"(\d+)\s*(jam|hari|minggu|bulan)", text.lower())
    if not m:
        return None
    return int(m.group(1)) * {"jam": 0, "hari": 1, "minggu": 7, "bulan": 30}[m.group(2)]


def decide(answers: dict, red_flags: list[str]) -> dict:
    """Mengembalikan arahan tingkat perawatan. Bila ragu, pilih yang lebih aman."""
    if red_flags:
        found = ", ".join(sorted(set(red_flags)))
        return {"arahan": DARURAT, "alasan": [f"Terdeteksi tanda bahaya: {found}."]}

    sev = parse_severity(answers.get("keparahan", ""))
    days = parse_days(answers.get("durasi", ""))
    if sev is not None and sev >= 9:
        return {"arahan": DARURAT, "alasan": [f"Keparahan sangat tinggi ({sev}/10)."]}

    alasan = []
    if sev is None:
        alasan.append("Tingkat keparahan tidak jelas, dipilih opsi yang lebih aman.")
    elif sev >= 6:
        alasan.append(f"Keparahan {sev}/10.")
    if days is None:
        alasan.append("Durasi tidak jelas, dipilih opsi yang lebih aman.")
    elif days >= 3:
        alasan.append(f"Keluhan berlangsung {days} hari.")

    if alasan:
        return {"arahan": KONSULTASI, "alasan": alasan}
    return {"arahan": MANDIRI, "alasan": ["Keluhan tampak ringan dan singkat."]}


def build_summary(answers: dict, hasil: dict) -> dict:
    return {
        "keluhan": answers.get("keluhan", ""),
        "durasi": answers.get("durasi", ""),
        "keparahan": answers.get("keparahan", ""),
        "riwayat": answers.get("riwayat", ""),
        "obat": answers.get("obat", ""),
        "alergi": answers.get("alergi", ""),
        "arahan_ai": hasil["arahan"],
        "alasan": hasil["alasan"],
        "status": "Belum Diverifikasi",
        "dokter_id": None,
        "catatan_dokter": None,
    }
