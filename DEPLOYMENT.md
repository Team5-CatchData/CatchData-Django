# CatchData Django 프로젝트 AWS EC2 배포 가이드

이 문서는 CatchData Django 프로젝트를 AWS EC2 인스턴스에 배포하는 방법을 설명합니다.

(수정)
개발 환경이 변함에 따라 해당 파일은 참고용으로 두었으며, 초기 환경 설정에만 쓰이고 있습니다.

README.md파일을 읽고 배포해주세요

## 목차

1. [사전 요구사항](#사전-요구사항)
2. [EC2 인스턴스 생성](#ec2-인스턴스-생성)
3. [프로젝트 배포](#프로젝트-배포)
4. [환경 설정](#환경-설정)
5. [서비스 관리](#서비스-관리)
6. [문제 해결](#문제-해결)
7. [보안 설정](#보안-설정)

---

## 사전 요구사항

### AWS 계정 및 리소스
- AWS 계정
- EC2 인스턴스 (Ubuntu 20.04 또는 22.04 권장)
- 보안 그룹 설정:
  - SSH (포트 22) - 본인 IP로 제한 권장
  - HTTP (포트 80) - 모든 IP 허용
  - HTTPS (포트 443) - 모든 IP 허용 (선택사항)

### 로컬 환경
- SSH 클라이언트
- PEM 키 파일 (EC2 인스턴스 접속용)

---

## EC2 인스턴스 생성

### 1. AWS Console에서 EC2 인스턴스 생성

1. **EC2 대시보드**로 이동
2. **인스턴스 시작** 클릭
3. 다음 설정 선택:
   - **AMI**: Ubuntu Server 22.04 LTS
   - **인스턴스 타입**: t2.micro (프리티어) 또는 t2.small
   - **키 페어**: 새로 생성하거나 기존 키 사용
   - **보안 그룹**:
     - SSH (22) - 내 IP
     - HTTP (80) - 0.0.0.0/0
     - HTTPS (443) - 0.0.0.0/0 (선택)

### 2. 인스턴스 접속

```bash
# PEM 키 권한 설정 (최초 1회)
chmod 400 your-key.pem

# SSH 접속
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

---

## 프로젝트 배포

### 방법 1: 자동 설치 스크립트 사용 (권장)

```bash
# 1. setup.sh 다운로드
cd ~
wget https://raw.githubusercontent.com/Team5-CatchData/CatchData-Django/main/setup.sh

# 2. 실행 권한 부여
chmod +x setup.sh

# 3. 스크립트 실행
./setup.sh
```

### 방법 2: 수동 설치

<details>
<summary>수동 설치 과정 보기</summary>

```bash
# 1. 시스템 업데이트
sudo apt-get update
sudo apt-get upgrade -y

# 2. Python 3.11 설치
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip

# 3. 프로젝트 클론
git clone https://github.com/Team5-CatchData/CatchData-Django.git
cd CatchData-Django

# 4. 가상환경 생성 및 활성화
python3.11 -m venv venv
source venv/bin/activate

# 5. 패키지 설치
pip install -r requirements.txt

# 6. Django 설정
cd FinalProject_Django
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput

# 7. Nginx 및 Gunicorn 설치
sudo apt-get install -y nginx
```

</details>

---

## 환경 설정

### 1. .env 파일 설정

```bash
nano ~/CatchData-Django/FinalProject_Django/.env
```

다음 내용을 입력하거나 수정:

```env
# Django Settings
SECRET_KEY=your-secret-key-here-generate-new-one
DEBUG=False
ALLOWED_HOSTS=your-ec2-public-ip,your-domain.com

# Kakao Map API
KAKAO_MAP_API_KEY=카카오맵 키

# Database (선택사항 - PostgreSQL 사용 시)
# DB_NAME=catchdata
# DB_USER=postgres
# DB_PASSWORD=your-secure-password
# DB_HOST=localhost
# DB_PORT=5432
```

> **! 중요**:
> - `SECRET_KEY`는 반드시 새로운 값으로 변경하세요
> - [Django Secret Key Generator](https://djecrety.ir/)에서 생성 가능
> - `ALLOWED_HOSTS`에 EC2 퍼블릭 IP 또는 도메인 추가

### 2. settings.py 확인

```bash
nano ~/CatchData-Django/FinalProject_Django/DE7FP_Django/settings.py
```

다음 설정이 올바른지 확인:

```python
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Kakao Map API
KAKAO_MAP_API_KEY = os.getenv('KAKAO_MAP_API_KEY', '')
```

### 3. Nginx 설정

```bash
sudo nano /etc/nginx/sites-available/catchdata
```

`server_name`을 실제 도메인 또는 IP로 변경:

```nginx
server {
    listen 80;
    server_name YOUR_EC2_PUBLIC_IP;  # 또는 도메인명

    client_max_body_size 10M;

    location = /favicon.ico {
        access_log off;
        log_not_found off;
    }

    location /static/ {
        alias /home/ubuntu/CatchData-Django/FinalProject_Django/staticfiles/;
    }

    location /media/ {
        alias /home/ubuntu/CatchData-Django/FinalProject_Django/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 서비스 관리

### 서비스 시작/중지/재시작

```bash
# Gunicorn 서비스
sudo systemctl start gunicorn      # 시작
sudo systemctl stop gunicorn       # 중지
sudo systemctl restart gunicorn    # 재시작
sudo systemctl status gunicorn     # 상태 확인

# Nginx 서비스
sudo systemctl start nginx
sudo systemctl stop nginx
sudo systemctl restart nginx
sudo systemctl status nginx
```

### 로그 확인

```bash
# Gunicorn 로그
sudo journalctl -u gunicorn -f
sudo tail -f /var/log/gunicorn/error.log
sudo tail -f /var/log/gunicorn/access.log

# Nginx 로그
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Django 로그 (설정한 경우)
tail -f ~/CatchData-Django/FinalProject_Django/logs/django.log
```

### 코드 업데이트

```bash
# 1. 프로젝트 디렉토리로 이동
cd ~/CatchData-Django

# 2. 최신 코드 pull
git pull origin main

# 3. 가상환경 활성화
source venv/bin/activate

# 4. 패키지 업데이트 (필요시)
pip install -r requirements.txt

# 5. 마이그레이션 실행 (필요시)
cd FinalProject_Django
python manage.py migrate

# 6. Static 파일 재수집
python manage.py collectstatic --noinput

# 7. Gunicorn 재시작
sudo systemctl restart gunicorn
```

---

##  문제 해결

### 1. Gunicorn이 시작되지 않는 경우

```bash
# 1. 상태 확인
sudo systemctl status gunicorn

# 2. 로그 확인
sudo journalctl -u gunicorn -n 50

# 3. 수동으로 Gunicorn 실행하여 오류 확인
cd ~/CatchData-Django/FinalProject_Django
source ../venv/bin/activate
gunicorn --config ../gunicorn_config.py DE7FP_Django.wsgi:application
```

### 2. Static 파일이 로드되지 않는 경우

```bash
# 1. Static 파일 재수집
cd ~/CatchData-Django/FinalProject_Django
source ../venv/bin/activate
python manage.py collectstatic --noinput

# 2. 권한 확인
sudo chown -R ubuntu:ubuntu ~/CatchData-Django/FinalProject_Django/staticfiles/

# 3. Nginx 설정 확인
sudo nginx -t
sudo systemctl restart nginx
```

### 3. 502 Bad Gateway 오류

```bash
# 1. Gunicorn이 실행 중인지 확인
sudo systemctl status gunicorn

# 2. Gunicorn이 포트 8000에서 listening 중인지 확인
sudo netstat -tuln | grep 8000

# 3. SELinux 비활성화 (필요한 경우)
sudo setenforce 0
```

### 4. 데이터베이스 연결 오류

```bash
# 1. 마이그레이션 상태 확인
cd ~/CatchData-Django/FinalProject_Django
source ../venv/bin/activate
python manage.py showmigrations

# 2. 마이그레이션 재실행
python manage.py migrate

# 3. SQLite 파일 권한 확인
ls -la db.sqlite3
```

---

## 🔒 보안 설정

### 1. Django Secret Key 변경

```bash
# Python 쉘에서 새 Secret Key 생성
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# .env 파일에 새 키 적용
nano ~/CatchData-Django/FinalProject_Django/.env
```

### 2. 방화벽 설정 (UFW)

```bash
# UFW 활성화
sudo ufw enable

# SSH 허용 (IMPORTANT: SSH 차단되지 않도록!)
sudo ufw allow OpenSSH

# Nginx 허용
sudo ufw allow 'Nginx Full'

# 상태 확인
sudo ufw status
```

### 3. Fail2Ban 설치 (선택사항)

```bash
# SSH 무차별 대입 공격 방지
sudo apt-get install -y fail2ban
sudo systemctl start fail2ban
sudo systemctl enable fail2ban
```

### 4. SSL/HTTPS 설정 (Let's Encrypt)

```bash
# Certbot 설치
sudo apt-get install -y certbot python3-certbot-nginx

# SSL 인증서 발급 (도메인이 있는 경우)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 자동 갱신 설정 확인
sudo systemctl status certbot.timer
```

---

## 📊 모니터링

### 시스템 리소스 확인

```bash
# CPU, 메모리 사용량
htop

# 디스크 사용량
df -h

# 프로세스 확인
ps aux | grep gunicorn
ps aux | grep nginx
```

### 서비스 상태 모니터링

```bash
# 모든 서비스 상태 확인
sudo systemctl list-units --type=service --state=running

# 특정 서비스 자동 시작 확인
sudo systemctl is-enabled gunicorn
sudo systemctl is-enabled nginx
```

---

## 🌐 접속 확인

배포가 완료되면 다음 URL로 접속:

```
http://YOUR_EC2_PUBLIC_IP
```

또는 도메인을 설정한 경우:

```
https://yourdomain.com
```

---

## 📝 추가 참고사항

### 데이터베이스 백업

```bash
# SQLite 백업
cp ~/CatchData-Django/FinalProject_Django/db.sqlite3 ~/backups/db_$(date +%Y%m%d).sqlite3

# PostgreSQL 백업 (사용하는 경우)
pg_dump -U postgres catchdata > ~/backups/catchdata_$(date +%Y%m%d).sql
```

### 정기 백업 Cron 설정

```bash
# Crontab 편집
crontab -e

# 매일 새벽 2시에 백업
0 2 * * * cp ~/CatchData-Django/FinalProject_Django/db.sqlite3 ~/backups/db_$(date +\%Y\%m\%d).sqlite3
```

---

## 🆘 추가 도움말

### db.sqlite3는 테스트 데이터용 DB

### 유용한 링크

- [Django 공식 문서](https://docs.djangoproject.com/)
- [Nginx 공식 문서](https://nginx.org/en/docs/)
- [Gunicorn 공식 문서](https://docs.gunicorn.org/)
- [AWS EC2 사용 설명서](https://docs.aws.amazon.com/ec2/)

### 문제 발생 시

1. 로그 파일 확인
2. 서비스 상태 확인
3. 설정 파일 검증
4. GitHub Issues에 문의

---

## 📄 라이선스

이 프로젝트는 [Team5-CatchData](https://github.com/Team5-CatchData)에서 관리합니다.

---

**마지막 업데이트**: 2025년 12월 16일
