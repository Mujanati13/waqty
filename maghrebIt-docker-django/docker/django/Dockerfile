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
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /src

# Copy wait script
#COPY docker/django/wait-for-it.sh /wait-for-it.sh
#RUN chmod +x /wait-for-it.sh

# Install Python dependencies
COPY /src/requirements.txt /src/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY /src/ /src/

# Run Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
