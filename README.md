# WiFi Management System

## Overview
A full‑stack web application for managing a campus Wi‑Fi network. It provides:
- Student authentication and client monitoring.
- Admin dashboard with client management, bandwidth control, web‑filtering, logs, and reporting.
- RESTful API built with **Flask** and **MongoDB**.
- Modern, responsive frontend built with vanilla HTML/CSS/JS.

## Features
- **Student portal** – login, view usage, request bandwidth.
- **Admin portal** – manage clients, block/unblock sites, toggle category filters, view logs, generate reports, bulk CSV upload.
- **Network security** – LAN‑only access, IP‑based session tracking.
- **Dynamic UI** – smooth animations, dark mode, glass‑morphism styling.

## Project Structure
```
wifi-management/
├─ Backend/            # Flask server
│  ├─ app.py
│  ├─ admin_routes.py
│  ├─ auth_routes.py
│  ├─ db.py
│  └─ ...
├─ Frontend/          # Static assets
│  ├─ Login/
│  └─ Final Admin/
└─ README.md
```

## Setup
### 1. Clone the repository
```bash
git clone https://github.com/Hitesh1477/wifi-management.git
cd wifi-management
```
### 2. Backend (Flask)
```bash
cd Backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
python app.py
```
The API will be available at `http://127.0.0.1:5000`.

### 3. Database (MongoDB)
- Install **MongoDB Community Server** and ensure the service is running.
- Open **MongoDB Compass** and create a database named `studentapp`.
- Create the following collections:
  - `users`
  - `admins`
  - `active_sessions`
  - `blocked_users`
  - `web_filter`
  - `logs`
- (Optional) Insert an admin document:
```json
{ "username": "admin", "password": "<hashed_password>" }
```
You can generate the hash with Python:
```python
from werkzeug.security import generate_password_hash
print(generate_password_hash('Admin@123'))
```

### 4. Frontend
Open the login page in a browser (you can use a simple static server or VS Code Live Server):
```
http://127.0.0.1:5500/Backend/Frontend/Login/index.html
```
The admin dashboard is reachable after logging in as an admin:
```
http://127.0.0.1:5500/Backend/Frontend/Final%20Admin/admin.html
```

## API Endpoints
### Auth routes (`/api/auth`)
- `POST /signup` – Register a student.
- `POST /login` – Student login, returns JWT.
- `POST /logout` – End session.
- `POST /admin/login` – Admin login, returns admin JWT.

### Admin routes (`/api` – routes already include `/admin` prefix)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/clients` | List all student clients. |
| POST | `/admin/clients` | Add a new client. |
| PATCH | `/admin/clients/<id>` | Update client fields (e.g., bandwidth limit, block status). |
| GET | `/admin/filtering` | Retrieve manual block list and category states. |
| POST | `/admin/filtering/sites` | Add a manual block URL. |
| DELETE | `/admin/filtering/sites` | Remove a manual block URL. |
| POST | `/admin/filtering/categories` | Toggle a category's active flag. |
| GET | `/admin/logs` | Fetch recent log entries. |
| GET | `/admin/stats` | Dashboard summary (client count, total data, threats blocked). |
| POST | `/admin/reports` | Generate a report (`type` and `range` in body). |
| POST | `/admin/bulk-upload` | Upload CSV to add multiple clients. |
All admin endpoints require a valid JWT with `role: "admin"` in the `Authorization: Bearer <token>` header.

## Running the Application
1. Start MongoDB.
2. Launch the Flask backend (`python app.py`).
3. Open the frontend login page in a browser.
4. Use the admin credentials to access the admin dashboard.

## Contributing
Feel free to open issues or submit pull requests. Please follow the existing code style and run the test suite before submitting changes.

## License
This project is licensed under the MIT License.
