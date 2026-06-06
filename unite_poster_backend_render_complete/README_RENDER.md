# Unite Poster Backend - Render Complete Package

Đây là bộ backend FastAPI hoàn chỉnh cho hướng đi mới:

**Frontend**: Netlify  
**Data/Auth/Storage**: Supabase  
**Image Backend**: Render Web Service chạy Docker + FastAPI

## 1. File có trong bộ này

```text
unite_poster_backend_render_complete/
├── app/
│   ├── __init__.py
│   ├── auth.py
│   ├── config.py
│   ├── image_autofit.py
│   ├── image_remove_bg.py
│   ├── main.py
│   ├── poster_render.py
│   └── supabase_client.py
├── Dockerfile
├── requirements.txt
├── render.yaml
├── supabase_backend_extension.sql
├── .env.example
├── .gitignore
├── README.md
└── README_RENDER.md
```

## 2. Chạy SQL mở rộng trong Supabase

Vào:

```text
Supabase → SQL Editor → New query
```

Copy toàn bộ nội dung file:

```text
supabase_backend_extension.sql
```

Dán vào SQL Editor rồi bấm **Run**.

File này tạo thêm:

- `poster_jobs`
- `poster_outputs`

## 3. Tạo GitHub repo

Vào GitHub → New repository:

```text
Repository name: unite-poster-backend
Visibility: Private hoặc Public đều được
Không tick README / gitignore / license
```

## 4. Push code lên GitHub

Trong terminal / Cloud Shell, vào thư mục này rồi chạy:

```bash
git init
git add .
git commit -m "Initial Unite poster FastAPI backend"
git branch -M main
git remote add origin https://github.com/TEN_GITHUB_CUA_BAN/unite-poster-backend.git
git push -u origin main
```

## 5. Tạo Web Service trên Render

Vào Render:

```text
New + → Web Service → Connect GitHub → chọn repo unite-poster-backend
```

Cấu hình:

```text
Name: unite-poster-backend
Runtime: Docker
Branch: main
Dockerfile Path: ./Dockerfile
Region: Singapore nếu có
Plan: Free hoặc Starter
```

## 6. Environment Variables trên Render

Vào mục **Environment**, thêm:

```env
APP_NAME=Unite Poster Backend
APP_ENV=production
DEBUG=false
PORT=8080

SUPABASE_URL=https://kclwqffwkxraryunmssd.supabase.co
SUPABASE_ANON_KEY=sb_publishable_uoozzSc1UTJEpCxZbJ1Ndw_7M6QZP2x
SUPABASE_BUCKET=poster-assets

SUPABASE_SERVICE_ROLE_KEY=DAN_SECRET_KEY_DEFAULT_CUA_SUPABASE_VAO_DAY

AUTO_UPLOAD_OUTPUTS=true
JOB_LOGGING_ENABLED=true
REQUIRE_AUTH_FOR_MUTATIONS=false
```

**Không đưa `SUPABASE_SERVICE_ROLE_KEY` lên GitHub.**
Chỉ dán key này vào Render Environment.

Lấy key ở:

```text
Supabase → Project Settings → API Keys → Copy secret key (default)
```

## 7. Deploy

Bấm:

```text
Create Web Service
```

Render sẽ build Docker image và chạy backend.

## 8. Test sau deploy

Render sẽ cấp link dạng:

```text
https://unite-poster-backend.onrender.com
```

Test health:

```text
https://unite-poster-backend.onrender.com/health
```

Nếu đúng sẽ thấy:

```json
{
  "ok": true,
  "app": "Unite Poster Backend",
  "env": "production",
  "supabase_configured": true
}
```

Test API docs:

```text
https://unite-poster-backend.onrender.com/docs
```

## 9. API có sẵn

### Remove background

```http
POST /api/remove-bg
```

Dùng để xóa nền ảnh nhân sự và upload PNG lên Supabase Storage.

### Auto-fit person

```http
POST /api/auto-fit-person
```

Dùng để xóa nền + tính vị trí `x`, `y`, `scale` phù hợp với vùng người.

### Render poster

```http
POST /api/render-poster
```

Dùng để render poster final bằng Python và upload ảnh hoàn chỉnh lên Supabase Storage.

## 10. Bước tiếp theo

Sau khi Render deploy xong, gửi lại backend URL cho mình, ví dụ:

```text
https://unite-poster-backend-xxxx.onrender.com
```

Mình sẽ gắn frontend v4 thành bản v5 để gọi backend Render thật.
