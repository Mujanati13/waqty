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

# Backend Configuration
BACKEND_PORT="${BACKEND_PORT:-5013}"
DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-changeme-$(openssl rand -base64 32)}"
DJANGO_DEBUG="${DJANGO_DEBUG:-False}"
ALLOWED_HOSTS="${ALLOWED_HOSTS:-localhost,127.0.0.1}"

# Frontend Configuration
FRONTEND_PORT="${FRONTEND_PORT:-5014}"
API_BASE_URL="${API_BASE_URL:-http://localhost:$BACKEND_PORT/api}"

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

# MySQL Root Password
MYSQL_ROOT_PASSWORD=$DB_ROOT_PASSWORD
MYSQL_DATABASE=$DB_NAME
MYSQL_USER=$DB_USER
MYSQL_PASSWORD=$DB_PASSWORD
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
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p${MYSQL_ROOT_PASSWORD}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - maghrebit_network

  backend:
    build:
      context: .
      dockerfile: docker/django/Dockerfile
    container_name: maghrebit-backend
    restart: always
    command: >
      sh -c "python manage.py migrate &&
             python manage.py collectstatic --noinput &&
             gunicorn maghrebIt_backend.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=${DEBUG}
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - DB_HOST=db
      - DB_PORT=3306
    volumes:
      - /home/debian/storage:/storage
      - /home/debian/storage/media:/storage/media
      - /home/debian/storage/documents:/storage/documents
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
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /src

# Install Python dependencies
COPY /src/requirements.txt /src/
RUN pip install --no-cache-dir -r requirements.txt

# Install gunicorn if not in requirements
RUN pip install gunicorn

# Copy project files
COPY /src/ /src/

# Create staticfiles directory
RUN mkdir -p /src/staticfiles

# Expose port
EXPOSE 8000

# Run Django with gunicorn
CMD ["gunicorn", "maghrebIt_backend.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
DOCKERFILE

log_success "Dockerfile updated"

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
sleep 15

# Check if backend is running
if docker ps | grep -q maghrebit-backend; then
    log_success "Backend container is running"
else
    log_error "Backend container failed to start"
    docker-compose logs backend
    exit 1
fi

# Check if database is running
if docker ps | grep -q maghrebit-mysql; then
    log_success "Database container is running"
else
    log_error "Database container failed to start"
    docker-compose logs db
    exit 1
fi

log_success "Backend deployed successfully"

# =============================================================================
# Frontend Deployment
# =============================================================================

log_info "Deploying frontend..."

cd $FRONTEND_DIR

# Update API endpoint in the frontend
log_info "Updating frontend API configuration..."
cat > src/helper/endpoint.js << EOF
// API Base URL Configuration
export const API_BASE_URL = '${API_BASE_URL}';

// Authentication Endpoints
export const AUTH_ENDPOINTS = {
  LOGIN_ESN: \`\${API_BASE_URL}/login_esn/\`,
  LOGIN_CONSULTANT: \`\${API_BASE_URL}/login_consultant/\`,
  LOGOUT: \`\${API_BASE_URL}/logout/\`,
};

// ESN Endpoints
export const ESN_ENDPOINTS = {
  LIST: \`\${API_BASE_URL}/ESN/\`,
  DETAIL: (id) => \`\${API_BASE_URL}/ESN/\${id}\`,
};

// Collaborateur/Consultant Endpoints
export const CONSULTANT_ENDPOINTS = {
  LIST: \`\${API_BASE_URL}/collaborateur/\`,
  DETAIL: (id) => \`\${API_BASE_URL}/collaborateur/\${id}\`,
  PROFILE: (id) => \`\${API_BASE_URL}/consultants/\${id}/profile/\`,
  DASHBOARD: (id) => \`\${API_BASE_URL}/consultants/\${id}/dashboard/\`,
  PROJECTS: (id) => \`\${API_BASE_URL}/consultant/\${id}/projects/\`,
  BY_ESN: (esnId) => \`\${API_BASE_URL}/consultants_par_esn/?esn_id=\${esnId}\`,
};

// Project Endpoints (BDC - Bon de Commande)
export const PROJECT_ENDPOINTS = {
  CREATE_BY_ESN: \`\${API_BASE_URL}/esn/create-project/\`,
  LIST: \`\${API_BASE_URL}/Bondecommande/\`,
  DETAIL: (id) => \`\${API_BASE_URL}/Bondecommande/\${id}\`,
  UPDATE_CONSULTANTS: (bdcId) => \`\${API_BASE_URL}/esn/project/\${bdcId}/consultants/\`,
  MANAGE_CONSULTANTS: (bdcId) => \`\${API_BASE_URL}/esn/project/\${bdcId}/consultants/manage/\`,
};

// BDC Endpoints (Alias for PROJECT_ENDPOINTS for backward compatibility)
export const BDC_ENDPOINTS = PROJECT_ENDPOINTS;

// CRA Imputation Endpoints (Daily entries)
export const CRA_IMPUTATION_ENDPOINTS = {
  LIST: \`\${API_BASE_URL}/cra_imputation\`,
  DETAIL: (id) => \`\${API_BASE_URL}/cra_imputation/\${id}/\`,
  BY_CONSULTANT: (consultantId, period) => 
    \`\${API_BASE_URL}/cra-by-period/?consultant_id=\${consultantId}&period=\${period}\`,
  BY_ESN: (esnId, period) => 
    \`\${API_BASE_URL}/cra-by-esn-period/?esn_id=\${esnId}&period=\${period}\`,
};

// CRA Consultant Endpoints (Monthly summaries)
export const CRA_CONSULTANT_ENDPOINTS = {
  LIST: \`\${API_BASE_URL}/cra_consultant/\`,
  DETAIL: (id) => \`\${API_BASE_URL}/cra_consultant/\${id}/\`,
  BY_CONSULTANT: (consultantId, period) => 
    \`\${API_BASE_URL}/cra-by-consultant-period/?consultant_id=\${consultantId}&period=\${period}\`,
  BY_PROJECT: (projectId, period) => 
    \`\${API_BASE_URL}/cra-by-project-period/?project_id=\${projectId}&period=\${period}\`,
  SUBMIT: (id) => \`\${API_BASE_URL}/cra_consultant/\${id}/submit/\`,
  VALIDATE: (id) => \`\${API_BASE_URL}/cra_consultant/\${id}/validate/\`,
};

// Notification Endpoints
export const NOTIFICATION_ENDPOINTS = {
  LIST: \`\${API_BASE_URL}/notifications/\`,
  MARK_READ: (id) => \`\${API_BASE_URL}/notifications/\${id}/mark-read/\`,
  MARK_ALL_READ: \`\${API_BASE_URL}/notifications/mark-all-read/\`,
};

// Document Endpoints
export const DOCUMENT_ENDPOINTS = {
  UPLOAD: \`\${API_BASE_URL}/documents/upload/\`,
  LIST: \`\${API_BASE_URL}/documents/\`,
  DETAIL: (id) => \`\${API_BASE_URL}/documents/\${id}\`,
};
EOF

log_success "Frontend API configuration updated"

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

# Create Nginx configuration
sudo tee $NGINX_CONF > /dev/null << 'NGINXCONF'
server {
    listen 80;
    server_name _;

    client_max_body_size 100M;

    # Frontend
    location / {
        proxy_pass http://localhost:5014;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:5013/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
        send_timeout 300;
    }

    # Django Admin
    location /admin/ {
        proxy_pass http://localhost:5013/admin/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
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
}
NGINXCONF

# Enable site
sudo ln -sf $NGINX_CONF $NGINX_ENABLED

# Test Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
sudo systemctl enable nginx

log_success "Nginx configured successfully"

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
log_success "Frontend URL: http://localhost or http://YOUR_VPS_IP"
log_success "Backend API: http://localhost/api or http://YOUR_VPS_IP/api"
log_success "Django Admin: http://localhost/admin or http://YOUR_VPS_IP/admin"
echo ""
log_info "Database: MySQL on port 3307 (mapped from container)"
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
log_info "  - Restart backend: cd $BACKEND_DIR && docker compose restart backend"
log_info "  - Restart frontend: pm2 restart mci-mini"
log_info "  - Restart all: cd $BACKEND_DIR && docker compose restart && pm2 restart all"
echo ""
log_warning "IMPORTANT: Update ALLOWED_HOSTS in .env with your domain/IP!"
log_warning "IMPORTANT: Change default database passwords in production!"
echo ""
log_success "Deployment completed successfully! 🎉"
echo ""
