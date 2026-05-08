# How to Run
cd /Users/vitopagone/Projects/kitaly
source venv/bin/activate
python run.py

Open a terminal in this folder:

```bash
cd /Users/vitopagone/Projects/kitaly
```

Activate the virtual environment:

```bash
source venv/bin/activate
```

If dependencies are not installed yet, run:

```bash
pip install -r requirements.txt
```

Make sure MySQL is running.

Make sure the `.env` file exists and contains a working `DATABASE_URL`, for example:

```env
DATABASE_URL=mysql+pymysql://YOUR_USER:YOUR_PASSWORD@localhost:3306/kitaly?charset=utf8mb4
SECRET_KEY=dev-secret
ADMIN_PASSWORD=your-admin-password
UPLOAD_FOLDER=uploads
FLASK_ENV=development
PORT=5001
```

If the database does not exist yet, create it:

```bash
mysql -u YOUR_USER -p -e "CREATE DATABASE IF NOT EXISTS kitaly CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

Run database migrations:

```bash
flask --app run.py db upgrade
```

Start the app:

```bash
python run.py
```

Open the app here:

```text
http://127.0.0.1:5001
```

Admin login:

```text
http://127.0.0.1:5001/admin/login
```

Use the password from `ADMIN_PASSWORD` in `.env`.

