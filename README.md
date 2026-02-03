# Kitaly - Football Shirt Catalog Management System

<div align="center">

![Kitaly Logo](static/images/logo.png)

A modern web application for cataloging and managing football shirt collections.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange.svg)](https://mysql.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Overview

Kitaly provides a public-facing catalog for fans and collectors alongside a secure admin dashboard for managing inventory, images, and descriptions. It supports multilingual content (English and Italian) and optional AI-assisted translation.

---

## Features

### Public Catalog
- Advanced filtering by brand, team, league, color, season, and more
- Full-text search across teams, brands, leagues, and descriptions
- Sorting by newest, oldest, price, or alphabetical order
- Responsive card layout optimized for all devices
- Detailed shirt pages with multiple images

### Admin Dashboard
- Secure authentication for admins
- Full CRUD management of shirts and images
- Batch operations for efficient updates
- Client and server-side validation

### Image Management
- Multi-image upload with cover selection
- Structured file organization by league and brand
- Optional image optimization and resizing

### AI Integration
- Optional AI translation between English and Italian
- Optional assistance for product descriptions

### UI/UX
- Tailwind CSS for consistent styling
- Lucide icons
- Mobile-first layout

---

## Tech Stack

### Backend
- Flask 3.0+
- SQLAlchemy
- MySQL 8.0+
- Flask-Migrate (Alembic)
- Flask-Login
- Flask-Babel
- Pillow

### Frontend
- Jinja2 templates
- Tailwind CSS (CDN)
- Vanilla JavaScript (ES6+)

### Infrastructure
- Gunicorn (production)
- Nginx (reverse proxy)
- Local filesystem storage
- python-dotenv

---

## Quick Start

### Prerequisites
- Python 3.8+
- MySQL 8.0+
- Git

### Installation

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/kitaly.git
   cd kitaly
   ```

2. Create and activate a virtual environment
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your configuration:
   ```env
   DATABASE_URL=mysql+pymysql://user:password@localhost:3306/kitaly?charset=utf8mb4
   SECRET_KEY=your-super-secret-key-here
   UPLOAD_FOLDER=uploads
   MAX_CONTENT_LENGTH=16777216
   ADMIN_PASSWORD=your-secure-admin-password
   OPENROUTER_API_KEY=your-openrouter-api-key
   FLASK_ENV=development
   PORT=5001
   ```

5. Set up the database
   ```bash
   mysql -u root -p -e "CREATE DATABASE kitaly CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
   export FLASK_APP=run.py
   flask db upgrade
   ```

6. Create upload directories
   ```bash
   mkdir -p uploads
   chmod 755 uploads
   ```

7. Run the application
   ```bash
   python run.py
   ```

---

## Project Structure

```
kitaly/
├── app/                          # Main application package
│   ├── __init__.py              # App factory and configuration
│   ├── models.py                # Database models
│   ├── auth.py                  # Authentication utilities
│   ├── openrouter.py            # AI integration
│   └── blueprints/              # Application blueprints
│       ├── admin.py             # Admin routes
│       └── public.py            # Public routes
├── migrations/                  # Database migrations
├── templates/                   # Jinja2 templates
├── static/                      # Static assets
├── uploads/                     # User-uploaded content
├── translations/                # Internationalization files
├── tests/                       # Test suite
├── requirements.txt             # Python dependencies
├── run.py                       # Application entry point
├── .env                         # Environment variables
└── README.md
```

---

## Database Schema

### Shirts Table
| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Primary key |
| `player_name` | VARCHAR(100) | Player name (optional) |
| `brand` | VARCHAR(100) | Manufacturer |
| `squadra` | VARCHAR(100) | Team name |
| `campionato` | VARCHAR(100) | League/Competition |
| `taglia` | VARCHAR(10) | Size |
| `colore` | VARCHAR(50) | Primary color |
| `stagione` | VARCHAR(20) | Season |
| `tipologia` | VARCHAR(50) | Shirt type |
| `type` | VARCHAR(50) | Additional classification |
| `maniche` | VARCHAR(50) | Sleeve type |
| `player_issued` | BOOLEAN | Player-issued version |
| `nazionale` | BOOLEAN | National team shirt |
| `prezzo_pagato` | FLOAT | Purchase price |
| `descrizione` | TEXT | Description (English) |
| `descrizione_ita` | TEXT | Description (Italian) |
| `status` | VARCHAR(20) | Record status |
| `created_at` | DATETIME | Creation timestamp |

### Shirt Images Table
| Field | Type | Description |
|-------|------|-------------|
| `id` | INT | Primary key |
| `shirt_id` | INT | Foreign key to shirts |
| `file_path` | VARCHAR(255) | Image file path |
| `is_cover` | BOOLEAN | Cover image flag |
| `created_at` | DATETIME | Upload timestamp |

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | MySQL connection string |
| `SECRET_KEY` | Yes | - | Flask secret key |
| `ADMIN_PASSWORD` | Yes | - | Admin dashboard password |
| `UPLOAD_FOLDER` | No | `uploads` | Image upload directory |
| `MAX_CONTENT_LENGTH` | No | `16777216` | Max upload size (bytes) |
| `OPENROUTER_API_KEY` | No | - | AI translation API key |
| `FLASK_ENV` | No | `development` | Environment mode |
| `PORT` | No | `5001` | Application port |

---

## Internationalization

### Adding a New Language

1. Extract translatable strings
   ```bash
   pybabel extract -F babel.cfg -k _l -o messages.pot .
   ```

2. Create a translation file
   ```bash
   pybabel init -i messages.pot -d translations -l es
   ```

3. Translate strings in `translations/es/LC_MESSAGES/messages.po`

4. Compile translations
   ```bash
   pybabel compile -d translations
   ```

### Supported Languages
- English (en)
- Italian (it)

---

## Production Deployment

### Option 1: Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5001

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5001", "run:app"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "5001:5001"
    environment:
      - FLASK_ENV=production
    volumes:
      - ./uploads:/app/uploads
    depends_on:
      - db
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: kitaly
    volumes:
      - mysql_data:/var/lib/mysql
volumes:
  mysql_data:
```

### Option 2: Traditional Setup

1. Install Gunicorn
   ```bash
   pip install gunicorn
   ```

2. Run with Gunicorn
   ```bash
   gunicorn -w 4 -b 127.0.0.1:8000 run:app
   ```

3. Configure Nginx
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       location /uploads/ {
           alias /path/to/kitaly/uploads/;
           expires 1y;
           add_header Cache-Control "public, immutable";
       }

       location /static/ {
           alias /path/to/kitaly/static/;
           expires 1y;
           add_header Cache-Control "public, immutable";
       }
   }
   ```

4. Set up SSL with Certbot
   ```bash
   sudo certbot --nginx -d yourdomain.com
   ```

---

## Testing

```bash
python -m pytest
python -m pytest --cov=app
python -m pytest tests/test_models.py
```

---

## API Endpoints

### Public
- `GET /` - Home page / catalog
- `GET /catalogue` - Catalog listing
- `GET /shirt/<id>` - Shirt detail page

### Admin
- `GET /admin` - Admin dashboard
- `GET /admin/login` - Admin login
- `POST /admin/login` - Admin authentication
- `GET /admin/shirt/new` - Create new shirt
- `POST /admin/shirt/new` - Save new shirt
- `GET /admin/shirt/<id>/edit` - Edit shirt
- `POST /admin/shirt/<id>/edit` - Update shirt
- `POST /admin/shirt/<id>/delete` - Delete shirt
- `POST /admin/upload` - Upload images

---

## Release

- Release notes are tracked in `CHANGELOG.md`.
- Releases are tagged in git using semantic versioning (e.g., `v1.2.0`).
- For a new release: update the changelog, tag the commit, and publish the release on your hosting platform.

---

## Security

- Session-based authentication for the admin dashboard
- SQLAlchemy ORM parameterization to mitigate SQL injection
- File upload validation and sanitized filenames
- Environment-based configuration for secrets

---

## Contributing

See `CONTRIBUTING.md` for guidelines.

---

## License

This project is licensed under the MIT License. See `LICENSE` for details.
