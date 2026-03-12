# Lung Disease Detector AI

This project is an AI-assisted chest X-ray triage system that predicts 8 distinct lung diseases using a custom-built DenseNet121 Deep Learning model.

## Project Structure
- **Backend**: Django API, Celery (for async model inference), TensorFlow/Keras
- **Frontend**: React + Vite + TailwindCSS

---

## Prerequisites
Before you begin, ensure you have the following installed on your machine:
1. **Python 3.10+**
2. **Node.js (v18+)** and **npm**
3. **Redis Server** (Required for Celery task queuing)
   - *Windows users*: You can install [Memurai](https://www.memurai.com/) (a Windows-native Redis port) or run Redis via WSL (Windows Subsystem for Linux).

---

## Getting Started: Step-by-Step

### 1. Clone the Repository
Open your terminal or command prompt and run:
```bash
git clone <your-repository-url>
cd clg_project
```

### 2. Backend Setup (Django & AI Model)
Open a terminal window and navigate to the backend folder:
```bash
cd backend
```

**Create and activate a virtual environment:**
```bash
# On Windows:
python -m venv venv
.\venv\Scripts\activate

# On Mac/Linux:
python3 -m venv venv
source venv/bin/activate
```

**Install the required Python packages:**
```bash
pip install -r requirements.txt
```

**Run Database Migrations:**
```bash
python manage.py makemigrations
python manage.py migrate
```

**Create an Admin Account (Superuser):**
This account will allow you to access the Admin Dashboard.
```bash
python manage.py createsuperuser
# Follow the prompts to set a username, email, and password.
```

### 3. Start the Backend Servers
You will need **three separate terminal windows** to run the complete backend.

**Terminal 1: Start Redis**
If you installed Memurai on Windows, it typically runs in the background automatically as a service. If using standard Redis, start the server:
```bash
redis-server
```

**Terminal 2: Start Django API**
*(Make sure your `venv` is activated)*
```bash
cd backend
python manage.py runserver
```

**Terminal 3: Start Celery Worker**
*(Make sure your `venv` is activated)*
```bash
cd backend

# On Windows:
celery -A backend worker -l INFO --pool=solo

# On Mac/Linux:
celery -A backend worker -l INFO
```

### 4. Frontend Setup (React/Vite)
Open a **fourth terminal window** and navigate to the frontend folder:
```bash
cd frontend
```

**Install Node dependencies:**
```bash
npm install
```

**Start the Vite development server:**
```bash
npm run dev
```

---

## Accessing the Application

- **Web Application**: Open your browser and go to `http://localhost:5173/`
- **Django Admin Panel**: Open your browser and go to `http://localhost:8000/admin/` (Login with the superuser account you created).

### Usage Notes:
- Non-admin users can register normally via the web interface.
- Only users marked as `is_superuser` (like the one created via `createsuperuser`) will see the **Dashboard** link in the navigation bar to view full system analytics and retraining controls.
- Upload an X-Ray image (PNG/JPG) on the main page to test the AI prediction engine!
