# gunicorn_config.py
import multiprocessing

# 워커 프로세스 수 (CPU 코어 * 2 + 1이 권장)
workers = multiprocessing.cpu_count() * 2 + 1

# 바인딩할 주소 (localhost:8000)
bind = '127.0.0.1:8000'

# 워커 클래스
worker_class = 'sync'

# 최대 요청 수 (메모리 누수 방지)
max_requests = 1000
max_requests_jitter = 50

# 타임아웃
timeout = 30

# 로그
accesslog = '-'  # stdout으로 출력
errorlog = '-'
loglevel = 'info'