from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login(role):
    r = client.post("/auth/login", json={"name": "Uji", "role": role})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def consent(h, granted=True):
    return client.post("/consents", json={"granted": granted}, headers=h)


def test_tanpa_consent_ditolak():
    h = login("pasien")
    assert client.post("/intake/sessions", headers=h).status_code == 403


def test_alur_lengkap_sampai_verifikasi_dokter():
    p, d = login("pasien"), login("dokter")
    consent(p)
    sid = client.post("/intake/sessions", headers=p).json()["session_id"]
    for ans in ["batuk ringan", "1 hari", "3", "tidak ada", "tidak ada", "tidak ada"]:
        r = client.post(f"/intake/sessions/{sid}/messages", json={"text": ans}, headers=p)
    assert r.json()["done"] and r.json()["result"]["arahan"] == "MANDIRI"

    # dokter belum bisa melihat sebelum pasien membagikan
    assert sid not in [x["session_id"] for x in client.get("/summaries", headers=d).json()]
    client.post(f"/intake/sessions/{sid}/share", headers=p)
    assert sid in [x["session_id"] for x in client.get("/summaries", headers=d).json()]

    client.patch(f"/summaries/{sid}/verify", json={"catatan": "OK"}, headers=d)
    hasil = client.get(f"/intake/sessions/{sid}/result", headers=p).json()
    assert hasil["summary"]["status"] == "Terverifikasi"


def test_red_flag_mengakhiri_sesi_darurat():
    p = login("pasien")
    consent(p)
    sid = client.post("/intake/sessions", headers=p).json()["session_id"]
    r = client.post(f"/intake/sessions/{sid}/messages", json={"text": "nyeri dada"}, headers=p)
    assert r.json()["done"] and r.json()["result"]["arahan"] == "DARURAT"


def test_peran_dan_audit():
    p, a = login("pasien"), login("admin")
    assert client.get("/summaries", headers=p).status_code == 403
    assert client.get("/admin/audit-logs", headers=p).status_code == 403
    assert client.get("/admin/audit-logs", headers=a).status_code == 200


def test_consent_dicabut_menghentikan_intake():
    p = login("pasien")
    consent(p)
    sid = client.post("/intake/sessions", headers=p).json()["session_id"]
    consent(p, False)
    r = client.post(f"/intake/sessions/{sid}/messages", json={"text": "batuk"}, headers=p)
    assert r.status_code == 403
