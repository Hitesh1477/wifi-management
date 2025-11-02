🚀 Project Setup Guide (Team Use Only)

 ✅ 1. Clone the Repository

git clone https://github.com/<your-username>/<repo-name>.git

✅ 2. Backend Setup (Flask)
Go to backend folder

cd Backend

Create Virtual Environment
python -m venv venv

Activate Virtual Environment
venv\Scripts\activate
pip install -r requirements.txt

Run Backend Server
python app.py
Backend will run on http://127.0.0.1:5000

✅ 3. Database Setup (MongoDB)
Make sure MongoDB is installed & running.

Install MongoDB Community Server (if not installed)

Open MongoDB Compass

Create database name: studentapp

Create collection: users

Add student manually or via signup API.

✅ 4. Frontend Setup
Go to Frontend folder:

http://127.0.0.1:5500/Backend/Frontend/Login/index.html

index.html → login page

home.html → dashboard page after login

🎯 Done!
Now the project should work:

Login page → index.html

Flask API running → http://127.0.0.1:5000

If any issue occurs, make sure:

Virtual environment is activated

MongoDB is running

Correct DB name: studentapp
