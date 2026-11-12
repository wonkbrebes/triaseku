# TriaseKu (demo akademik)

Aplikasi pendamping pra-konsultasi: intake gejala, triase 3 tingkat
(Darurat / Konsultasi / Mandiri), ringkasan untuk dokter, consent, dan audit log.
Sesuai MRD/PRD/Desain. AI hanya mengarahkan, bukan mendiagnosis. Gunakan data sintetis.

## Struktur
- `backend/`  FastAPI (API, logika triase, tes, Dockerfile)
- `mobile/`   Flutter (alur pasien: login, consent, chat, hasil, bagikan)
- `.github/workflows/ci.yml`  lint, tes, gate skenario AI, build image, Trivy, build APK
- `docker-compose.yml`, `scripts/setup_android.sh`

## Jalankan backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q                          # tes + gate keselamatan
uvicorn app.main:app --reload      # http://localhost:8000/docs
# atau: docker compose up --build
```

## Jalankan di Android
```bash
cd mobile
bash ../scripts/setup_android.sh   # sekali saja: membuat folder android/
flutter run                        # emulator (memakai 10.0.2.2:8000)
# HP asli (satu Wi-Fi dengan laptop):
flutter run --dart-define=API_URL=http://IP_LAPTOP:8000
flutter build apk                  # file APK
```

## Peran dokter dan admin
Belum ada layar mobile untuk dokter/admin; gunakan Swagger di `/docs`
(login dengan role `dokter` atau `admin`, lalu klik Authorize dengan token):
`GET /summaries` -> `PATCH /summaries/{id}/verify`, dan `GET /admin/audit-logs`.

## Cakupan terhadap PRD
FR-01 (login versi demo), FR-02, FR-03, FR-04, FR-05, FR-06, FR-07, FR-08, FR-09, FR-10 selesai.
Belum: OTP asli, notifikasi (FR-11), dasbor admin (FR-12), FHIR (FR-13), pengingat (FR-14).

## Catatan keterbatasan
- Penyimpanan in-memory (hilang saat restart). Berikutnya: PostgreSQL + enkripsi kolom.
- Pertanyaan intake masih terskrip. Titik sambung LLM: `triage.next_question`.
- Deteksi tanda bahaya berbasis kata kunci, sehingga kalimat negasi ("tidak nyeri dada")
  tetap terdeteksi. Ini disengaja (lebih aman), tetapi bisa over-triage.
- HTTP lokal hanya untuk pengembangan; demo/produksi wajib HTTPS.
