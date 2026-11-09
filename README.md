# 🁣 domino 101

Real-vaxt çoxoyunçulu domin (2/3/4 nəfər, 101 xal, Google ilə giriş, səs effektləri).
Stack: Flask + Flask-SocketIO + Vanilla JS. Səslər WebAudio ilə yaradılır (fayl lazım deyil).

## Lokal işə salma
```bash
pip install -r requirements.txt
python app.py        # http://localhost:5000
```

## GitHub
```bash
git init && git add . && git commit -m "xnxx 101"
git branch -M main
git remote add origin https://github.com/<istifadəçi>/xnxx-101.git
git push -u origin main
```

## Render-də yerləşdirmə
1. render.com → **New → Blueprint** (və ya Web Service) → GitHub repo-nu seçin (`render.yaml` avtomatik oxunur).
2. Environment: `GOOGLE_CLIENT_ID` = Google Cloud-dan aldığınız Client ID.
3. Deploy. Başlanğıc: `gunicorn --worker-class gthread --threads 100 -w 1 -b 0.0.0.0:$PORT app:app`
   (**-w 1** vacibdir: otaqlar yaddaşda saxlanılır).

## Google ilə giriş
console.cloud.google.com → APIs & Services → Credentials → **OAuth client ID (Web)**.
*Authorized JavaScript origins*: `https://<app-adınız>.onrender.com` (və lokal üçün `http://localhost:5000`).
Client ID-ni `GOOGLE_CLIENT_ID` kimi əlavə edin. Təyin olunmasa, yalnız "Qonaq" girişi işləyir.

## Qaydalar
- 28 daş qarışdırılır (SystemRandom), hər kəsə 7 daş.
- İlk əl: ən kiçik qoşa (1-1, 2-2 … 6-6, 0-0) ilə başlanır; sonrakı əlləri əli bitirən başlayır.
- 2 nəfər: bazardan yalnız cüt, bazarda son 2 daş qalır. 3 nəfər: tək-tək, son 1 daş qalır. İstənilən vaxt bazara getmək olar.
- 4 nəfər: bazar yoxdur, qarşı-qarşıya oturanlar cütdür, xallar birlikdə sayılır.
- Əli bitirən (və ya bağlanmada ən az xallı) rəqiblərin əlində qalan daşların xalını alır. 101-ə çatan qalib.
