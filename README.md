# Kitaly - Shirt Catalog Web App

A modern, minimal full-stack web application for cataloging football shirts.

## Features
- **Public Catalog**: Filterable grid of shirts with search and sorting.
- **Admin Dashboard**: Secure management area for CRUD operations.
- **Multi-Image Upload**: Drag-and-drop interface with instant previews and cover selection.
- **Responsive Design**: Elegant UI built with Tailwind CSS and Lucide icons.

## Tech Stack
- **Backend**: Python Flask, SQLAlchemy, Flask-Migrate, PyMySQL
- **Frontend**: Jinja2 Templates, Tailwind CSS (CDN), Lucide Icons
- **Database**: MySQL

## Local Setup

1. **Clone the repository**
2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure Environment**
   Edit the `.env` file with your database credentials:
   ```env
   DATABASE_URL=mysql+pymysql://user:pass@host:3306/db?charset=utf8mb4
   SECRET_KEY=your-secret-key
   UPLOAD_FOLDER=uploads
   ADMIN_PASSWORD=your-secure-password
   ```
5. **Initialize Database**
   ```bash
   export FLASK_APP=run.py
   flask db upgrade
   ```
6. **Run the Application**
   ```bash
   python run.py
   ```
   The app will be available at `http://localhost:5001`.

## Production Deployment (Nginx + Gunicorn)

### 1. Gunicorn
Install Gunicorn on your server and run the app:
```bash
gunicorn -w 4 -b 127.0.0.1:8000 run:app
```

### 2. Nginx Configuration
Setup a reverse proxy in your Nginx config:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /uploads/ {
        alias /path/to/kitaly/uploads/;
    }

    location /static/ {
        alias /path/to/kitaly/static/;
    }
}
```

### 3. File Permissions
Ensure the `uploads` directory is writable by the user running Gunicorn:
```bash
chmod -R 755 uploads
```
