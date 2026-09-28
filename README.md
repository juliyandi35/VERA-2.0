# V.E.R.A.

V.E.R.A. (Virtual Enhance Research Assistant) adalah ruang kerja riset AI lokal
berbasis Flask dan Ollama. Antarmuka tersedia lebih dulu, sementara komponen AI,
RAG, visi, dan transkripsi dimuat hanya saat benar-benar diperlukan.

## Menjalankan

Jalankan perintah berikut dari PowerShell:

    C:\Users\juliy\anaconda3\python.exe -m pip install -r requirements.txt
    C:\Users\juliy\anaconda3\python.exe app.py

Buka http://127.0.0.1:5000/, atau jalankan VERA.bat.

## Konfigurasi

Simpan nilai yang diperlukan di .env. Jangan simpan nilainya di Git.

- VERA_MODEL — model Ollama, bawaan gemma4:12b
- VERA_CONTEXT_WINDOW — ukuran konteks, bawaan 8192
- VERA_HOST dan VERA_PORT — alamat server lokal
- VERA_DEBUG — isi 1 hanya saat pengembangan
- OPEN_WEATHER_API_KEY — data cuaca
- SENDER_EMAIL dan SENDER_PASSWORD — pengiriman email
- GOOGLE_API_KEY, SUPABASE_DB_URI, SPREADSHEET_ID, SHEET_NAME,
  RECIPIENT_EMAIL, dan HF_TOKEN — konfigurasi integrasi yang sudah ada

## Pemeriksaan

    C:\Users\juliy\anaconda3\python.exe -m pytest -q
    node --check static\js\vera.js
