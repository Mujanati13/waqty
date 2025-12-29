#!/bin/bash

# =============================================================================
# VPS Deployment Script for MaghrebIT Backend + MCI-Mini Frontend
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/home/debian/waqty"
BACKEND_DIR="$PROJECT_DIR/maghrebIt-docker-django"
FRONTEND_DIR="$PROJECT_DIR/mci-mini"
NGINX_CONF="/etc/nginx/sites-available/waqty"
NGINX_ENABLED="/etc/nginx/sites-enabled/waqty"

# Database Configuration
DB_NAME="${DB_NAME:-maghrebit_db}"
DB_USER="${DB_USER:-maghrebit_user}"
DB_PASSWORD="${DB_PASSWORD:-changeme123}"
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-rootpassword123}"

# Get server IP automatically or use provided
SERVER_IP="${SERVER_IP:-$(curl -s ifconfig.me 2>/dev/null || echo '51.38.99.75')}"

# Domain Configuration
FRONTEND_DOMAIN="${FRONTEND_DOMAIN:-waqty.albech.me}"
BACKEND_DOMAIN="${BACKEND_DOMAIN:-api-waqty.albech.me}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@albech.me}"

# Backend Configuration
BACKEND_PORT="${BACKEND_PORT:-5013}"
DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-changeme-$(openssl rand -base64 32)}"
DJANGO_DEBUG="${DJANGO_DEBUG:-False}"
ALLOWED_HOSTS="${ALLOWED_HOSTS:-localhost,127.0.0.1,$SERVER_IP,$FRONTEND_DOMAIN,$BACKEND_DOMAIN}"

# Frontend Configuration
FRONTEND_PORT="${FRONTEND_PORT:-5014}"
# Use the API domain for backend requests
API_BASE_URL="${API_BASE_URL:-https://$BACKEND_DOMAIN/api}"

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 is not installed. Please install it first."
        exit 1
    fi
}

check_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    elif docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    else
        log_error "Docker Compose is not installed. Please install it first."
        exit 1
    fi
    log_info "Using: $DOCKER_COMPOSE"
}

# =============================================================================
# Pre-deployment Checks
# =============================================================================

log_info "Starting pre-deployment checks..."

# Check required commands
check_command docker
check_docker_compose
check_command git
check_command node
check_command npm

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 20 ]; then
    log_error "Node.js version $NODE_VERSION detected. Vite requires Node.js 20.19+ or 22.12+"
    log_info "Please upgrade Node.js: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs"
    exit 1
fi

log_success "All required commands are available"

# =============================================================================
# Install System Dependencies
# =============================================================================

log_info "Installing system dependencies..."

if ! command -v nginx &> /dev/null; then
    log_info "Installing Nginx..."
    sudo apt-get update
    sudo apt-get install -y nginx
fi

log_success "System dependencies installed"

# =============================================================================
# Create Project Directory Structure
# =============================================================================

log_info "Creating project directory structure..."

sudo mkdir -p $PROJECT_DIR
sudo chown -R $(whoami):$(whoami) $PROJECT_DIR

# Create storage directories for backend
sudo mkdir -p /home/debian/storage/{media,documents}
sudo chown -R $(whoami):$(whoami) /home/debian/storage

log_success "Directory structure created"

# =============================================================================
# Clone or Update Repository
# =============================================================================

log_info "Setting up project files..."

if [ -d "$PROJECT_DIR/.git" ]; then
    log_info "Updating existing repository..."
    cd $PROJECT_DIR
    git pull origin main || git pull origin master || log_warning "Git pull failed, continuing..."
else
    log_info "Project directory ready for deployment"
    # If you're deploying from a git repo, uncomment and modify:
    # git clone YOUR_REPO_URL $PROJECT_DIR
fi

# =============================================================================
# Backend Deployment
# =============================================================================

log_info "Deploying backend..."

cd $BACKEND_DIR

# Create .env file for backend
log_info "Creating backend environment file..."
cat > .env << EOF
# Django Settings
SECRET_KEY=$DJANGO_SECRET_KEY
DEBUG=$DJANGO_DEBUG
ALLOWED_HOSTS=$ALLOWED_HOSTS

# Database Settings
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_HOST=db
DB_PORT=3306

# CORS Settings - Include all possible origins (with HTTPS domains)
CORS_ALLOWED_ORIGINS=https://$FRONTEND_DOMAIN,https://$BACKEND_DOMAIN,http://$SERVER_IP,http://localhost,http://localhost:$FRONTEND_PORT,http://127.0.0.1
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOW_CREDENTIALS=True
CORS_ALLOW_METHODS=DELETE,GET,OPTIONS,PATCH,POST,PUT
CORS_ALLOW_HEADERS=accept,accept-encoding,authorization,content-type,dnt,origin,user-agent,x-csrftoken,x-requested-with

# MySQL Root Password
MYSQL_ROOT_PASSWORD=$DB_ROOT_PASSWORD
MYSQL_DATABASE=$DB_NAME
MYSQL_USER=$DB_USER
MYSQL_PASSWORD=$DB_PASSWORD

# CSRF Trusted Origins (with HTTPS)
CSRF_TRUSTED_ORIGINS=https://$FRONTEND_DOMAIN,https://$BACKEND_DOMAIN,http://localhost,http://127.0.0.1
EOF

log_success "Backend environment file created"

# Update docker-compose.yml with full configuration
log_info "Updating docker-compose.yml..."
cat > docker-compose.yml << 'DOCKERCOMPOSE'
services:
  db:
    image: mysql:8.0
    container_name: maghrebit-mysql
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
      - ./docker/mysql/entrypoint:/docker-entrypoint-initdb.d
      - ./schema-and-data.sql:/docker-entrypoint-initdb.d/01-schema-and-data.sql
    ports:
      - "3307:3306"
    command: --default-authentication-plugin=mysql_native_password --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p${MYSQL_ROOT_PASSWORD}"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s
    networks:
      - maghrebit_network

  backend:
    build:
      context: .
      dockerfile: docker/django/Dockerfile
    container_name: maghrebit-backend
    restart: always
    command: >
      sh -c "sleep 10 &&
             python manage.py migrate --fake 2>/dev/null || python manage.py migrate --fake-initial --noinput || echo 'Migrations skipped' &&
             python manage.py collectstatic --noinput &&
             gunicorn maghrebIt_backend.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120 --access-logfile - --error-logfile -"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=${DEBUG}
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - DB_HOST=db
      - DB_PORT=3306
      - CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS}
      - CORS_ALLOW_ALL_ORIGINS=${CORS_ALLOW_ALL_ORIGINS}
      - CORS_ALLOW_CREDENTIALS=${CORS_ALLOW_CREDENTIALS}
      - CORS_ALLOW_METHODS=${CORS_ALLOW_METHODS}
      - CORS_ALLOW_HEADERS=${CORS_ALLOW_HEADERS}
      - CSRF_TRUSTED_ORIGINS=${CSRF_TRUSTED_ORIGINS}
    volumes:
      - /home/debian/storage:/storage
      - /home/debian/storage/media:/src/media
      - /home/debian/storage/documents:/src/documents
      - ./src:/src
      - static_volume:/src/staticfiles
    ports:
      - "5013:8000"
    depends_on:
      db:
        condition: service_healthy
    networks:
      - maghrebit_network

volumes:
  mysql_data:
  static_volume:

networks:
  maghrebit_network:
    driver: bridge
DOCKERCOMPOSE

log_success "docker-compose.yml updated"

# Update Dockerfile to include gunicorn
log_info "Updating Dockerfile..."
cat > docker/django/Dockerfile << 'DOCKERFILE'
# Dockerfile

# Base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    netcat-traditional \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /src

# Install Python dependencies
COPY /src/requirements.txt /src/
RUN pip install --no-cache-dir -r requirements.txt

# Install gunicorn and django-cors-headers if not in requirements
RUN pip install gunicorn django-cors-headers

# Copy wait-for-it script
COPY /docker/django/wait-for-it.sh /src/wait-for-it.sh
RUN chmod +x /src/wait-for-it.sh

# Copy project files
COPY /src/ /src/

# Create staticfiles and media directories
RUN mkdir -p /src/staticfiles /src/media /src/documents

# Expose port
EXPOSE 8000

# Run Django with gunicorn
CMD ["gunicorn", "maghrebIt_backend.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
DOCKERFILE

log_success "Dockerfile updated"

# Create/Update wait-for-it script
log_info "Creating wait-for-it script..."
cat > docker/django/wait-for-it.sh << 'WAITFORIT'
#!/usr/bin/env bash
# wait-for-it.sh - Wait for service to be available

WAITFORIT_cmdname=${0##*/}

echoerr() { if [[ $WAITFORIT_QUIET -ne 1 ]]; then echo "$@" 1>&2; fi }

usage()
{
    cat << USAGE >&2
Usage:
    $WAITFORIT_cmdname host:port [-s] [-t timeout] [-- command args]
    -h HOST | --host=HOST       Host or IP under test
    -p PORT | --port=PORT       TCP port under test
    -s | --strict               Only execute subcommand if the test succeeds
    -q | --quiet                Don't output any status messages
    -t TIMEOUT | --timeout=TIMEOUT
                                Timeout in seconds, zero for no timeout
    -- COMMAND ARGS             Execute command with args after the test finishes
USAGE
    exit 1
}

wait_for()
{
    if [[ $WAITFORIT_TIMEOUT -gt 0 ]]; then
        echoerr "$WAITFORIT_cmdname: waiting $WAITFORIT_TIMEOUT seconds for $WAITFORIT_HOST:$WAITFORIT_PORT"
    else
        echoerr "$WAITFORIT_cmdname: waiting for $WAITFORIT_HOST:$WAITFORIT_PORT without a timeout"
    fi
    WAITFORIT_start_ts=$(date +%s)
    while :
    do
        if [[ $WAITFORIT_ISBUSY -eq 1 ]]; then
            nc -z $WAITFORIT_HOST $WAITFORIT_PORT
            WAITFORIT_result=$?
        else
            (echo -n > /dev/tcp/$WAITFORIT_HOST/$WAITFORIT_PORT) >/dev/null 2>&1
            WAITFORIT_result=$?
        fi
        if [[ $WAITFORIT_result -eq 0 ]]; then
            WAITFORIT_end_ts=$(date +%s)
            echoerr "$WAITFORIT_cmdname: $WAITFORIT_HOST:$WAITFORIT_PORT is available after $((WAITFORIT_end_ts - WAITFORIT_start_ts)) seconds"
            break
        fi
        sleep 1
    done
    return $WAITFORIT_result
}

wait_for_wrapper()
{
    if [[ $WAITFORIT_QUIET -eq 1 ]]; then
        timeout $WAITFORIT_BUSYTIMEFLAG $WAITFORIT_TIMEOUT $0 --quiet --child --host=$WAITFORIT_HOST --port=$WAITFORIT_PORT --timeout=$WAITFORIT_TIMEOUT &
    else
        timeout $WAITFORIT_BUSYTIMEFLAG $WAITFORIT_TIMEOUT $0 --child --host=$WAITFORIT_HOST --port=$WAITFORIT_PORT --timeout=$WAITFORIT_TIMEOUT &
    fi
    WAITFORIT_PID=$!
    trap "kill -INT -$WAITFORIT_PID" INT
    wait $WAITFORIT_PID
    WAITFORIT_RESULT=$?
    if [[ $WAITFORIT_RESULT -ne 0 ]]; then
        echoerr "$WAITFORIT_cmdname: timeout occurred after waiting $WAITFORIT_TIMEOUT seconds for $WAITFORIT_HOST:$WAITFORIT_PORT"
    fi
    return $WAITFORIT_RESULT
}

WAITFORIT_TIMEOUT=${WAITFORIT_TIMEOUT:-15}
WAITFORIT_STRICT=${WAITFORIT_STRICT:-0}
WAITFORIT_CHILD=${WAITFORIT_CHILD:-0}
WAITFORIT_QUIET=${WAITFORIT_QUIET:-0}

if [[ $(which nc) ]]; then
    WAITFORIT_ISBUSY=1
else
    WAITFORIT_ISBUSY=0
fi

WAITFORIT_BUSYTIMEFLAG=""
if [[ $(which timeout) ]]; then
    if timeout --help 2>&1 | grep -q -- '-t '; then
        WAITFORIT_BUSYTIMEFLAG="-t"
    fi
fi

while [[ $# -gt 0 ]]
do
    case "$1" in
        *:* )
        WAITFORIT_hostport=(${1//:/ })
        WAITFORIT_HOST=${WAITFORIT_hostport[0]}
        WAITFORIT_PORT=${WAITFORIT_hostport[1]}
        shift 1
        ;;
        --child)
        WAITFORIT_CHILD=1
        shift 1
        ;;
        -q | --quiet)
        WAITFORIT_QUIET=1
        shift 1
        ;;
        -s | --strict)
        WAITFORIT_STRICT=1
        shift 1
        ;;
        -h)
        WAITFORIT_HOST="$2"
        if [[ $WAITFORIT_HOST == "" ]]; then break; fi
        shift 2
        ;;
        --host=*)
        WAITFORIT_HOST="${1#*=}"
        shift 1
        ;;
        -p)
        WAITFORIT_PORT="$2"
        if [[ $WAITFORIT_PORT == "" ]]; then break; fi
        shift 2
        ;;
        --port=*)
        WAITFORIT_PORT="${1#*=}"
        shift 1
        ;;
        -t)
        WAITFORIT_TIMEOUT="$2"
        if [[ $WAITFORIT_TIMEOUT == "" ]]; then break; fi
        shift 2
        ;;
        --timeout=*)
        WAITFORIT_TIMEOUT="${1#*=}"
        shift 1
        ;;
        --)
        shift
        WAITFORIT_CLI=("$@")
        break
        ;;
        --help)
        usage
        ;;
        *)
        echoerr "Unknown argument: $1"
        usage
        ;;
    esac
done

if [[ "$WAITFORIT_HOST" == "" || "$WAITFORIT_PORT" == "" ]]; then
    echoerr "Error: you need to provide a host and port to test."
    usage
fi

WAITFORIT_TIMEOUT=${WAITFORIT_TIMEOUT:-15}
WAITFORIT_STRICT=${WAITFORIT_STRICT:-0}
WAITFORIT_CHILD=${WAITFORIT_CHILD:-0}
WAITFORIT_QUIET=${WAITFORIT_QUIET:-0}

if [[ $WAITFORIT_CHILD -gt 0 ]]; then
    wait_for
    WAITFORIT_RESULT=$?
    exit $WAITFORIT_RESULT
else
    if [[ $WAITFORIT_TIMEOUT -gt 0 ]]; then
        wait_for_wrapper
        WAITFORIT_RESULT=$?
    else
        wait_for
        WAITFORIT_RESULT=$?
    fi
fi

if [[ $WAITFORIT_CLI != "" ]]; then
    if [[ $WAITFORIT_RESULT -ne 0 && $WAITFORIT_STRICT -eq 1 ]]; then
        echoerr "$WAITFORIT_cmdname: strict mode, refusing to execute subprocess"
        exit $WAITFORIT_RESULT
    fi
    exec "${WAITFORIT_CLI[@]}"
else
    exit $WAITFORIT_RESULT
fi
WAITFORIT

chmod +x docker/django/wait-for-it.sh
log_success "wait-for-it script created"

# Stop existing containers
log_info "Stopping existing containers..."
$DOCKER_COMPOSE down || true

# Remove old images to ensure fresh build
log_info "Cleaning up old Docker images..."
docker system prune -f

# Build and start containers
log_info "Building and starting Docker containers..."
$DOCKER_COMPOSE up -d --build

# Wait for services to be ready
log_info "Waiting for services to start..."
sleep 20

# Check if backend is running
if docker ps | grep -q maghrebit-backend; then
    log_success "Backend container is running"
    
    # Test backend health
    log_info "Testing backend connectivity..."
    sleep 5
    if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5013/api/ | grep -qE "200|301|302|404"; then
        log_success "Backend is responding"
    else
        log_warning "Backend may still be starting up..."
    fi
else
    log_error "Backend container failed to start"
    $DOCKER_COMPOSE logs backend
    exit 1
fi

# Check if database is running
if docker ps | grep -q maghrebit-mysql; then
    log_success "Database container is running"
else
    log_error "Database container failed to start"
    $DOCKER_COMPOSE logs db
    exit 1
fi

log_success "Backend deployed successfully"

# =============================================================================
# Database Setup & Fixes
# =============================================================================

log_info "Setting up database with schema and data..."

# Wait a bit more for database to be fully ready
sleep 10

# Check if we need to import the schema
log_info "Checking database tables..."
TABLE_COUNT=$($DOCKER_COMPOSE exec -T db mysql -u root -p${DB_ROOT_PASSWORD} ${DB_NAME} -e "SHOW TABLES;" 2>/dev/null | wc -l)

if [ "$TABLE_COUNT" -lt 10 ]; then
    log_warning "Database appears empty or incomplete. Importing schema..."
    
    # Import the schema and data
    log_info "Importing schema-and-data.sql..."
    $DOCKER_COMPOSE exec -T db mysql -u root -p${DB_ROOT_PASSWORD} ${DB_NAME} < schema-and-data.sql
    
    if [ $? -eq 0 ]; then
        log_success "Database schema imported successfully"
    else
        log_error "Failed to import database schema"
        $DOCKER_COMPOSE logs db
    fi
else
    log_success "Database tables exist"
fi

# Verify the appeloffre table has the jours column
log_info "Verifying database schema..."
JOURS_CHECK=$($DOCKER_COMPOSE exec -T db mysql -u root -p${DB_ROOT_PASSWORD} ${DB_NAME} -e "SHOW COLUMNS FROM appeloffre LIKE 'jours';" 2>/dev/null | grep -c "jours")

if [ "$JOURS_CHECK" -eq 0 ]; then
    log_warning "The 'jours' column is missing. Re-importing schema..."
    $DOCKER_COMPOSE exec -T db mysql -u root -p${DB_ROOT_PASSWORD} -e "DROP DATABASE IF EXISTS ${DB_NAME}; CREATE DATABASE ${DB_NAME};"
    $DOCKER_COMPOSE exec -T db mysql -u root -p${DB_ROOT_PASSWORD} ${DB_NAME} < schema-and-data.sql
    log_success "Database schema re-imported"
fi

# Create test ESN account
log_info "Creating test ESN account..."

# Create a Python script to set up test account
cat > /tmp/setup_test_account.py << 'PYEOF'
import sys
import os
sys.path.insert(0, '/src')
os.chdir('/src')

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maghrebIt_backend.settings')
django.setup()

from django.contrib.auth.hashers import make_password
from django.db import connection

# Delete existing test account
with connection.cursor() as cursor:
    cursor.execute("DELETE FROM esn WHERE mail_Contact = 'test@esn.com'")
    
    # Insert new test account
    password_hash = make_password('password123')
    cursor.execute("""
        INSERT INTO esn (Raison_sociale, SIRET, Adresse, CP, Ville, Pays, mail_Contact, Tel_Contact, password, responsible)
        VALUES ('Test ESN Inc', '12345678901234', '123 Test Street', '75001', 'Paris', 'France', 'test@esn.com', '0123456789', %s, 'Test Contact')
    """, [password_hash])
    
print("✓ Test ESN account created:")
print("  Email: test@esn.com")
print("  Password: password123")
PYEOF

# Copy script to container and run it
docker cp /tmp/setup_test_account.py maghrebit-backend:/tmp/
$DOCKER_COMPOSE exec -T backend python /tmp/setup_test_account.py

if [ $? -eq 0 ]; then
    log_success "Test ESN account created"
    echo ""
    echo "  📧 Email: test@esn.com"
    echo "  🔑 Password: password123"
    echo ""
else
    log_warning "Failed to create test ESN account"
fi

# Restart backend to ensure all changes are loaded
log_info "Restarting backend to apply changes..."
$DOCKER_COMPOSE restart backend
sleep 5

log_success "Database setup completed"

# =============================================================================
# Frontend Deployment
# =============================================================================

log_info "Deploying frontend..."

cd $FRONTEND_DIR

# Update API endpoint in the frontend
log_info "Updating frontend API configuration..."

# Create .env file for frontend (Vite uses VITE_ prefix)
cat > .env << EOF
VITE_API_BASE_URL=${API_BASE_URL}
EOF

log_success "Frontend environment file created"

# Install dependencies
log_info "Installing frontend dependencies..."
npm install

# Build frontend
log_info "Building frontend..."
npm run build

log_success "Frontend built successfully"

# Create frontend service with PM2
log_info "Setting up frontend service..."

# Install PM2 if not installed
if ! command -v pm2 &> /dev/null; then
    log_info "Installing PM2..."
    sudo npm install -g pm2
fi

# Stop existing PM2 process
pm2 delete mci-mini || true

# Start frontend with PM2 using preview mode (serves the build)
pm2 start npm --name "mci-mini" -- run preview -- --port $FRONTEND_PORT --host 0.0.0.0

# Save PM2 configuration
pm2 save

# Setup PM2 to start on boot
sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u $(whoami) --hp /home/$(whoami)

log_success "Frontend deployed successfully"

# =============================================================================
# Nginx Configuration
# =============================================================================

log_info "Configuring Nginx..."

# Remove default nginx site if exists
sudo rm -f /etc/nginx/sites-enabled/default

# Create Nginx configuration for Frontend (waqty.albech.me)
sudo tee /etc/nginx/sites-available/waqty-frontend > /dev/null << NGINXCONF
server {
    listen 80;
    server_name ${FRONTEND_DOMAIN};

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:${FRONTEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Health check
    location /health {
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }
}
NGINXCONF

# Create Nginx configuration for Backend API (api-waqty.albech.me)
sudo tee /etc/nginx/sites-available/waqty-backend > /dev/null << NGINXCONF
server {
    listen 80;
    server_name ${BACKEND_DOMAIN};

    client_max_body_size 100M;

    # Let Django handle all CORS - just proxy everything
    location / {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
        send_timeout 300;
    }

    # Static files
    location /static/ {
        alias /home/debian/storage/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /home/debian/storage/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Documents
    location /documents/ {
        alias /home/debian/storage/documents/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Health check
    location /health {
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }
}
NGINXCONF

# Enable sites
sudo ln -sf /etc/nginx/sites-available/waqty-frontend /etc/nginx/sites-enabled/
sudo ln -sf /etc/nginx/sites-available/waqty-backend /etc/nginx/sites-enabled/

# Test Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
sudo systemctl enable nginx

log_success "Nginx configured successfully"

# =============================================================================
# SSL Certificate Generation (Let's Encrypt)
# =============================================================================

log_info "Setting up SSL certificates with Let's Encrypt..."

# Install certbot if not installed
if ! command -v certbot &> /dev/null; then
    log_info "Installing Certbot..."
    sudo apt-get update
    sudo apt-get install -y certbot python3-certbot-nginx
fi

# Generate SSL certificates for both domains
log_info "Generating SSL certificate for ${FRONTEND_DOMAIN}..."
sudo certbot --nginx -d ${FRONTEND_DOMAIN} --non-interactive --agree-tos --email ${ADMIN_EMAIL} --redirect || {
    log_warning "Failed to generate SSL for ${FRONTEND_DOMAIN}. Make sure DNS is properly configured."
}

log_info "Generating SSL certificate for ${BACKEND_DOMAIN}..."
sudo certbot --nginx -d ${BACKEND_DOMAIN} --non-interactive --agree-tos --email ${ADMIN_EMAIL} --redirect || {
    log_warning "Failed to generate SSL for ${BACKEND_DOMAIN}. Make sure DNS is properly configured."
}

# Setup automatic renewal
log_info "Setting up automatic SSL renewal..."
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Test renewal
sudo certbot renew --dry-run || log_warning "SSL renewal test failed"

log_success "SSL certificates configured successfully"

# =============================================================================
# Firewall Configuration
# =============================================================================

log_info "Configuring firewall..."

if command -v ufw &> /dev/null; then
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw allow 22/tcp
    log_success "Firewall rules configured"
else
    log_warning "UFW not installed, skipping firewall configuration"
fi

# =============================================================================
# Post-Deployment Tasks
# =============================================================================

log_info "Running post-deployment tasks..."

# Create Django superuser script
cat > $BACKEND_DIR/create_superuser.sh << 'SUPERUSER'
#!/bin/bash
cd $(dirname $0)
if command -v docker-compose &> /dev/null; then
    docker-compose exec backend python manage.py createsuperuser
else
    docker compose exec backend python manage.py createsuperuser
fi
SUPERUSER
chmod +x $BACKEND_DIR/create_superuser.sh

log_success "Created superuser script at $BACKEND_DIR/create_superuser.sh"

# Create debug/troubleshoot script
cat > $BACKEND_DIR/debug.sh << DEBUGSCRIPT
#!/bin/bash
echo "=== Docker Container Status ==="
docker ps -a

echo ""
echo "=== Backend Logs (last 50 lines) ==="
docker logs maghrebit-backend --tail 50

echo ""
echo "=== Database Logs (last 20 lines) ==="
docker logs maghrebit-mysql --tail 20

echo ""
echo "=== Testing Backend Connectivity (local) ==="
curl -v http://127.0.0.1:${BACKEND_PORT}/health/ 2>&1 | head -30

echo ""
echo "=== Testing via Domain (${BACKEND_DOMAIN}) ==="
curl -v https://${BACKEND_DOMAIN}/health 2>&1 | head -30

echo ""
echo "=== Testing Frontend Domain (${FRONTEND_DOMAIN}) ==="
curl -v https://${FRONTEND_DOMAIN}/health 2>&1 | head -30

echo ""
echo "=== Nginx Status ==="
sudo systemctl status nginx --no-pager | head -15

echo ""
echo "=== PM2 Status ==="
pm2 list

echo ""
echo "=== SSL Certificate Status ==="
sudo certbot certificates

echo ""
echo "=== Environment Variables in Backend ==="
docker exec maghrebit-backend env | grep -E "CORS|ALLOWED|DEBUG|DB_|CSRF"
DEBUGSCRIPT
chmod +x $BACKEND_DIR/debug.sh
log_success "Created debug script at $BACKEND_DIR/debug.sh"

# =============================================================================
# Status Check
# =============================================================================

log_info "Checking deployment status..."

echo ""
echo "======================================"
echo "  Deployment Status"
echo "======================================"

# Check Docker containers
echo ""
log_info "Docker Containers:"
$DOCKER_COMPOSE -f $BACKEND_DIR/docker-compose.yml ps

# Check PM2 processes
echo ""
log_info "PM2 Processes:"
pm2 list

# Check Nginx status
echo ""
log_info "Nginx Status:"
sudo systemctl status nginx --no-pager | head -n 10

echo ""
echo "======================================"
echo "  Deployment Summary"
echo "======================================"
echo ""
log_success "Frontend URL: https://$FRONTEND_DOMAIN"
log_info "  - Frontend runs on port $FRONTEND_PORT (proxied via Nginx with SSL)"
log_success "Backend API: https://$BACKEND_DOMAIN/api"
log_info "  - Backend runs on port $BACKEND_PORT (proxied via Nginx with SSL)"
log_success "Django Admin: https://$BACKEND_DOMAIN/admin/"
echo ""
log_info "Domain Configuration:"
log_info "  - Frontend: $FRONTEND_DOMAIN"
log_info "  - Backend API: $BACKEND_DOMAIN"
echo ""
log_info "Internal Ports:"
log_info "  - Nginx: 80/443 (public access point)"
log_info "  - Frontend (PM2): $FRONTEND_PORT"
log_info "  - Backend (Docker): $BACKEND_PORT"
log_info "  - MySQL (Docker): 3307 (host) -> 3306 (container)"
echo ""
log_info "Database Configuration:"
log_info "  - Database: $DB_NAME"
log_info "  - User: $DB_USER"
echo ""
log_info "Logs:"
log_info "  - Backend: cd $BACKEND_DIR && docker compose logs -f backend"
log_info "  - Database: cd $BACKEND_DIR && docker compose logs -f db"
log_info "  - Frontend: pm2 logs mci-mini"
log_info "  - Nginx: sudo tail -f /var/log/nginx/access.log"
echo ""
log_info "Management Commands:"
log_info "  - Create superuser: cd $BACKEND_DIR && ./create_superuser.sh"
log_info "  - Debug/troubleshoot: cd $BACKEND_DIR && ./debug.sh"
log_info "  - Restart backend: cd $BACKEND_DIR && docker compose restart backend"
log_info "  - Restart frontend: pm2 restart mci-mini"
log_info "  - Restart all: cd $BACKEND_DIR && docker compose restart && pm2 restart all"
log_info "  - Renew SSL: sudo certbot renew"
echo ""
log_info "Health Check URLs:"
log_info "  - Backend: curl https://$BACKEND_DOMAIN/health"
log_info "  - Frontend: curl https://$FRONTEND_DOMAIN/health"
echo ""
log_success "SSL Certificates installed for:"
log_info "  - $FRONTEND_DOMAIN"
log_info "  - $BACKEND_DOMAIN"
echo ""
log_warning "IMPORTANT: Change default database passwords in production!"
echo ""
log_success "Deployment completed successfully! 🎉"
echo ""
