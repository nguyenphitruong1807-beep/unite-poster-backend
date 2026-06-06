# Unite Poster Backend Starter (FastAPI)

Bộ starter này dành cho tool poster của Hạnh, dùng để xử lý backend chuẩn chỉnh:

- **API xóa nền** ảnh nhân sự
- **API auto-fit** tính x/y/scale cho người vào `personSlot`
- **API render poster final** bằng Python
- **Kết nối Supabase** để:
  - xác thực user bằng Bearer token Supabase
  - upload file lên Supabase Storage
  - ghi `poster_jobs` và `poster_outputs`

---

## 1) Cấu trúc thư mục

```bash
poster_backend_starter/
├── app/
│   ├── auth.py
│   ├── config.py
│   ├── image_autofit.py
│   ├── image_remove_bg.py
│   ├── main.py
│   ├── poster_render.py
│   └── supabase_client.py
├── .env.example
├── Dockerfile
├── requirements.txt
├── README.md
└── supabase_backend_extension.sql
```

---

## 2) Chuẩn bị Supabase

Trước khi chạy backend:

1. Hạnh đã có project Supabase + bảng `profiles`, `poster_templates`, `poster_assets`.
2. Chạy thêm file SQL này trong **SQL Editor**:

```text
supabase_backend_extension.sql
```

File này tạo thêm:
- `poster_jobs`
- `poster_outputs`

---

## 3) Tạo file `.env`

Copy `.env.example` thành `.env` rồi điền:

```env
SUPABASE_URL=https://kclwqffwkxraryunmssd.supabase.co
SUPABASE_SERVICE_ROLE_KEY=PASTE_YOUR_SERVICE_ROLE_KEY_HERE
SUPABASE_ANON_KEY=sb_publishable_...
SUPABASE_BUCKET=poster-assets
```

> Quan trọng: `SUPABASE_SERVICE_ROLE_KEY` **chỉ để ở backend**, không đưa vào frontend.

### Lấy service role key ở đâu?
Supabase Dashboard → **Project Settings → API** → mục **service_role / secret**.

---

## 4) Chạy local

### Cài thư viện

```bash
python -m venv .venv
source .venv/bin/activate   # Mac/Linux
# hoặc .venv\Scripts\activate trên Windows
pip install -r requirements.txt
```

### Chạy API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Mở thử:

```text
http://localhost:8080/health
```

---

## 5) Chạy bằng Docker

### Build image

```bash
docker build -t unite-poster-backend .
```

### Run container

```bash
docker run --env-file .env -p 8080:8080 unite-poster-backend
```

---

## 6) Deploy Cloud Run (gợi ý)

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/unite-poster-backend

gcloud run deploy unite-poster-backend \
  --image gcr.io/YOUR_PROJECT_ID/unite-poster-backend \
  --platform managed \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars APP_ENV=production,SUPABASE_URL=...,SUPABASE_SERVICE_ROLE_KEY=...,SUPABASE_BUCKET=poster-assets
```

---

## 7) API có sẵn

### 7.1 Health check

```http
GET /health
```

---

### 7.2 Remove background

```http
POST /api/remove-bg
Content-Type: multipart/form-data
```

Fields:
- `file` (bắt buộc)
- `save_to_storage` = true/false
- `folder` = `processed/remove-bg`
- `output_name` (optional)
- `return_base64` = true/false

Ví dụ `curl`:

```bash
curl -X POST http://localhost:8080/api/remove-bg \
  -F "file=@./person.jpg" \
  -F "save_to_storage=true" \
  -F "folder=processed/remove-bg"
```

---

### 7.3 Auto-fit person

```http
POST /api/auto-fit-person
Content-Type: multipart/form-data
```

Fields:
- `file` hoặc `image_url`
- `slot_x`
- `slot_y`
- `slot_width`
- `slot_height`
- `anchor_y` = `bottom` | `center` | `belly`
- `fit_mode` = `head_to_belly`
- `save_removed_bg` = true/false
- `folder` = `processed/autofit`

Ví dụ `curl`:

```bash
curl -X POST http://localhost:8080/api/auto-fit-person \
  -F "file=@./person.jpg" \
  -F "slot_x=335" \
  -F "slot_y=420" \
  -F "slot_width=560" \
  -F "slot_height=650" \
  -F "anchor_y=bottom"
```

Kết quả sẽ trả về `x`, `y`, `scale`.

---

### 7.4 Render poster

```http
POST /api/render-poster
Content-Type: multipart/form-data
```

Fields:
- `template_json` (bắt buộc, string JSON)
- `texts_json` (string JSON)
- `person_x`
- `person_y`
- `person_scale`
- `background_file` hoặc `background_url`
- `foreground_file` hoặc `foreground_url`
- `person_file` hoặc `person_image_url`
- `save_to_storage` = true/false
- `output_folder` = `outputs/posters`
- `output_name` (optional)

Ví dụ `curl`:

```bash
curl -X POST http://localhost:8080/api/render-poster \
  -F 'template_json={"templateId":"best-seller-thang-5-2026","canvas":{"width":1229,"height":1536},"textFields":[{"key":"awardTitle","x":615,"y":280,"width":880,"fontSize":100,"fontWeight":"900","fontFamily":"Montserrat","color":"#ffffff","align":"center","fillType":"solid"}]}' \
  -F 'texts_json={"awardTitle":"BEST SELLER","name":"TRUONG"}' \
  -F "person_x=320" \
  -F "person_y=410" \
  -F "person_scale=0.82" \
  -F "background_file=@./bg.png" \
  -F "foreground_file=@./fg.png" \
  -F "person_file=@./person.png" \
  -F "save_to_storage=true"
```

---

## 8) Cách frontend gọi backend

### Luồng chuẩn
1. Frontend upload ảnh nhân sự.
2. Gọi `/api/remove-bg`.
3. Gọi `/api/auto-fit-person` để lấy `x/y/scale`.
4. Khi leader bấm xuất, gọi `/api/render-poster`.
5. Backend upload ảnh final lên Supabase Storage và trả URL.

### Gửi Bearer token Supabase
Nếu muốn backend biết user là ai / log job theo user:

```http
Authorization: Bearer <supabase_access_token>
```

---

## 9) Ghi chú kỹ thuật

- `remove-bg` dùng `rembg`
- `auto-fit` dùng alpha bounds + face detection Haar Cascade của OpenCV
- `render-poster` dùng Pillow
- Gradient chữ đã hỗ trợ ở mức starter
- Font riêng có thể dùng nếu trong `template.fonts` có `public_url` và `family`

---

## 10) Gợi ý bước tiếp theo

Sau khi backend chạy ổn, bước tiếp theo nên làm:

1. Gắn frontend v4 gọi backend thật
2. Lưu `job_id` và trạng thái render trong giao diện admin
3. Thêm batch render từ Excel
4. Lưu poster output vào màn hình lịch sử

Nếu Hạnh muốn, bước sau mình có thể làm tiếp:
- **frontend gọi thẳng backend này**, hoặc
- **bản batch render từ Excel/CSV**.
