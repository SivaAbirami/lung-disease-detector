## Lung Disease Detector – Full-Stack AI Web Application

AI-assisted lung disease screening (COVID-19, Tuberculosis, Bacterial/Viral Pneumonia, Normal) from chest X-rays using a Django REST backend, TensorFlow MobileNetV2 model, Celery/Redis async pipeline, PostgreSQL storage, and a React + Vite + TailwindCSS frontend.

### Backend stack
- Django 4 + Django REST Framework
- PostgreSQL + psycopg2
- Celery + Redis for async predictions
- TensorFlow/Keras (MobileNetV2 transfer learning)
- Pillow, OpenCV, NumPy for image handling

### Frontend stack
- React 18 + Vite
- TailwindCSS
- react-dropzone, axios, react-router, react-hot-toast

---

## 1. Datasets (MANUAL DOWNLOAD)

Download and extract these datasets from Kaggle:

- COVID-19 Radiography Database  
  Link: `https://www.kaggle.com/tawsifurrahman/covid19-radiography-database`

- TB Chest X-ray Database  
  Link: `https://www.kaggle.com/tawsifurrahman/tuberculosis-tb-chest-xray-dataset`

Place the images under `backend/dataset/combined/` in subfolders:

- `COVID-19/`
- `Tuberculosis/`
- `Bacterial Pneumonia/`
- `Viral Pneumonia/`
- `Normal/`

The training script will:
- Use 70%/15%/15% train/val/test split
- Apply augmentation and class weighting
- Train and fine-tune MobileNetV2
- Save the best model to `backend/ml_model/saved_models/model.h5`

Run training:

```bash
cd backend
python -m ml_model.train
```

---

## 2. Development environment setup

Prerequisites:
- Python 3.9+
- Node.js 16+
- PostgreSQL
- Redis

### 2.1 Backend (Django + Celery)

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # on Windows
pip install --upgrade pip
pip install -r requirements.txt
```

Create `.env` (see `backend/.env.example` for keys – if missing, use these):

- `DJANGO_SECRET_KEY=your-secret`
- `DEBUG=True`
- `ALLOWED_HOSTS=localhost,127.0.0.1`
- `CORS_ALLOWED_ORIGINS=http://localhost:5173`
- `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/lung_disease_db`
- `REDIS_URL=redis://localhost:6379/0`
- `CELERY_BROKER_URL=redis://localhost:6379/0`
- `CELERY_RESULT_BACKEND=redis://localhost:6379/1`
- `MODEL_PATH=ml_model/saved_models/model.h5`

Then:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Start Celery worker in a second terminal:

```bash
cd backend
venv\Scripts\activate  # on Windows
celery -A backend worker -l info
```

### 2.2 Frontend (React + Vite + Tailwind)

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173` and proxies `/api` to `http://localhost:8000`.

---

## 3. API overview

- `POST /api/predict/`
  - Multipart form: `image` (jpg/jpeg/png, max 10MB, min 224x224)
  - Response (cache hit):
    - `{ status: "completed", cached: true, prediction: {...} }`
  - Response (async):
    - `{ task_id: "...", status: "processing", cached: false, prediction_id: N }`

- `GET /api/task/<task_id>/`
  - Returns:
    - `{ status: "processing" }`
    - `{ status: "completed", prediction: {...} }`
    - `{ status: "failed", error: "..." }`

- `GET /api/predictions/?page=1&predicted_class=COVID-19&search=Normal`
  - Paginated history (10 per page).

- `GET /api/recommendations/<disease_name>/`
  - Returns structured recommendations for the given disease string.

The `prediction` object contains:
- `image_url`
- `predicted_class`, `confidence_score`, `confidence_percentage`
- `urgency_level`, `urgency_color`, `urgency_icon`
- `immediate_actions`, `medical_recommendations`, `lifestyle_recommendations`
- `follow_up`, `disclaimer`
- `created_at`, `processing_time_ms`, `cached_result`

---

## 4. Docker deployment

From `backend/`:

```bash
cd backend
docker-compose up --build
```

Services:
- `db` – PostgreSQL
- `redis` – Redis
- `backend` – Django + Gunicorn
- `celery` – Celery worker
- `frontend` – React build served by Nginx
- `nginx` – reverse proxy on port 80

Environment variables for production (example):

- `DJANGO_SECRET_KEY=...`
- `DATABASE_URL=postgresql://postgres:postgres@db:5432/lung_disease_db`
- `REDIS_URL=redis://redis:6379/0`
- `CELERY_BROKER_URL=redis://redis:6379/0`
- `CELERY_RESULT_BACKEND=redis://redis:6379/1`
- `MODEL_PATH=ml_model/saved_models/model.h5`
- `DEBUG=False`
- `ALLOWED_HOSTS=your-domain.com`
- `CORS_ALLOWED_ORIGINS=https://your-frontend-domain`

---

## 5. Usage flow (UI)

1. Open the frontend.
2. Go to **Upload**:
   - Drag & drop or browse a `.jpg`, `.jpeg`, `.png` X-ray (max 10MB, min 224x224).
   - Client-side checks for type, size, resolution.
   - Submit triggers:
     - Hash check on backend (duplicate images served instantly from cache).
     - Celery async task otherwise; frontend polls `/api/task/<id>/`.
3. You are redirected to **Result** view:
   - Urgency badge (color-coded).
   - Confidence bar.
   - Detailed disease-specific recommendations (immediate, medical, lifestyle, follow-up).
   - Downloadable PDF report.
4. **History** view:
   - Paginated, searchable history.
   - Filter by disease type.
   - Thumbnails with lazy loading.

---

## 6. Troubleshooting

- **Model path error**: make sure `MODEL_PATH` in `.env` points to `ml_model/saved_models/model.h5` and that the file exists (run training first).
- **Celery not processing**: verify Redis is running and `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` match Redis; check worker logs.
- **CORS errors**: ensure `CORS_ALLOWED_ORIGINS` in backend env includes the frontend URL (e.g., `http://localhost:5173`).
- **Database connection issues**: confirm `DATABASE_URL` points to a reachable PostgreSQL instance and that credentials match.
- **Static/media not served in Docker**: confirm volumes and Nginx config; check logs of `nginx` service.

---

## 7. Security notes

- Backend validates:
  - File extensions (`.jpg`, `.jpeg`, `.png`)
  - File size (max 10MB)
  - Magic bytes + Pillow verification to prevent renamed non-image uploads
  - Minimum dimensions (224x224)
- Filenames are sanitized and replaced with UUIDs.
- SHA-256 hashing ensures duplicate images are detected and served from cache.
- Use HTTPS and proper SSL in production (e.g., Nginx + Certbot).

