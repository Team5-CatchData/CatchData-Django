#!/bin/bash

# CatchData Django Project Setup Script for AWS EC2
# Ubuntu 20.04/22.04 기준

set -e  # 에러 발생 시 스크립트 중단

echo "================================================"
echo "CatchData Django Project Setup Starting..."
echo "================================================"

# 시스템 업데이트
echo "[1/10] Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# 필수 패키지 설치
echo "[2/10] Installing essential packages..."
sudo apt-get install -y git curl wget vim build-essential libssl-dev libffi-dev python3-dev

# Python 3.11 설치 (또는 Python 3.10+)
echo "[3/10] Installing Python 3.11..."
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip

# pip 업그레이드
echo "[4/10] Upgrading pip..."
python3.11 -m pip install --upgrade pip

# 프로젝트 디렉토리 생성 및 클론
echo "[5/10] Cloning project from GitHub..."
cd ~
if [ -d "CatchData-Django" ]; then
    echo "Project directory already exists. Pulling latest changes..."
    cd CatchData-Django
    git pull
else
    git clone https://github.com/Team5-CatchData/CatchData-Django.git
    cd CatchData-Django
fi

# 가상환경 생성 및 활성화
echo "[6/10] Creating virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Python 패키지 설치
echo "[7/10] Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    # requirements.txt가 없는 경우 기본 패키지 설치
    pip install django==5.2.6
    pip install python-dotenv
    pip install gunicorn
fi

# Nginx 설치
echo "[8/10] Installing Nginx..."
sudo apt-get install -y nginx

# .env 파일 설정 안내
echo "[9/10] Setting up environment variables..."
if [ ! -f "FinalProject_Django/.env" ]; then
    echo "Creating .env file template..."
    cat > FinalProject_Django/.env << EOF
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,your-ec2-ip

# Kakao Map API
KAKAO_MAP_API_KEY=f2837d1902b6ad83d2eb931b616129fc

# Database (if using PostgreSQL)
# DB_NAME=catchdata
# DB_USER=postgres
# DB_PASSWORD=your-password
# DB_HOST=localhost
# DB_PORT=5432
EOF
    echo "⚠️  Please edit FinalProject_Django/.env with your actual values!"
fi

# Django 설정
echo "[10/10] Configuring Django project..."
cd FinalProject_Django

# 마이그레이션 실행
python manage.py makemigrations
python manage.py migrate

# Static 파일 수집
python manage.py collectstatic --noinput

# Gunicorn 설정 파일 생성
echo "Creating Gunicorn configuration..."
cat > ~/CatchData-Django/gunicorn_config.py << EOF
import multiprocessing

# Gunicorn 설정
bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# 로깅
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"

# 프로세스 이름
proc_name = "catchdata_django"

# Daemon mode
daemon = False
EOF

# Gunicorn 로그 디렉토리 생성
sudo mkdir -p /var/log/gunicorn
sudo chown -R $USER:$USER /var/log/gunicorn

# Systemd 서비스 파일 생성 (Gunicorn)
echo "Creating Gunicorn systemd service..."
sudo tee /etc/systemd/system/gunicorn.service > /dev/null << EOF
[Unit]
Description=Gunicorn daemon for CatchData Django
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=/home/$USER/CatchData-Django/FinalProject_Django
Environment="PATH=/home/$USER/CatchData-Django/venv/bin"
ExecStart=/home/$USER/CatchData-Django/venv/bin/gunicorn \\
    --config /home/$USER/CatchData-Django/gunicorn_config.py \\
    DE7FP_Django.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

# Nginx 설정 파일 생성
echo "Creating Nginx configuration..."
sudo tee /etc/nginx/sites-available/catchdata << EOF
server {
    listen 80;
    server_name _;  # 도메인 또는 EC2 public IP로 변경하세요

    client_max_body_size 10M;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias /home/$USER/CatchData-Django/FinalProject_Django/staticfiles/;
    }

    location /media/ {
        alias /home/$USER/CatchData-Django/FinalProject_Django/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Nginx 설정 심볼릭 링크 생성
sudo ln -sf /etc/nginx/sites-available/catchdata /etc/nginx/sites-enabled/

# 기본 Nginx 설정 제거
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx 설정 테스트
echo "Testing Nginx configuration..."
sudo nginx -t

# 서비스 시작 및 활성화
echo "Starting services..."
sudo systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
sudo systemctl restart nginx
sudo systemctl enable nginx

# 방화벽 설정 (UFW 사용 시)
echo "Configuring firewall..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 'Nginx Full'
    sudo ufw allow OpenSSH
    sudo ufw --force enable
fi

echo "================================================"
echo "✅ Setup Complete!"
echo "================================================"
echo ""
echo "📋 Next Steps:"
echo "1. Edit .env file: nano ~/CatchData-Django/FinalProject_Django/.env"
echo "2. Update ALLOWED_HOSTS in settings.py with your domain/IP"
echo "3. Update Nginx server_name: sudo nano /etc/nginx/sites-available/catchdata"
echo "4. Restart services:"
echo "   sudo systemctl restart gunicorn"
echo "   sudo systemctl restart nginx"
echo ""
echo "🔍 Check Status:"
echo "   sudo systemctl status gunicorn"
echo "   sudo systemctl status nginx"
echo ""
echo "📝 View Logs:"
echo "   sudo journalctl -u gunicorn -f"
echo "   sudo tail -f /var/log/nginx/error.log"
echo ""
echo "🌐 Your site should be available at: http://YOUR_EC2_IP"
echo "================================================"
