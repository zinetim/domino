# gunicorn.conf.py
import multiprocessing

# Socket.IO üçün eventlet tövsiyə olunur (threading əvəzinə)
worker_class = "eventlet"

# Eventlet + WebSocket üçün 1 worker tövsiyə olunur (state paylaşımı üçün)
workers = 1

# Eventlet worker üçün threads istifadə olunmur
# threads = 100  # SİLİNDİ - eventlet ilə uyğun deyil

# Eventlet üçün timeout 0 (uzun bağlantılar üçün)
timeout = 120
graceful_timeout = 30
keepalive = 5

# Bağlantı limiti
worker_connections = 1000

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Ping/pong (Socket.IO üçün)
# (Flask-SocketIO öz ping_interval/ping_timeout istifadə edir)

# Yaddaş sızması qarşısı
max_requests = 1000
max_requests_jitter = 100

# Bağlanma
bind = "0.0.0.0:5000"
