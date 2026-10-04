# 🚀 AHMED VPN - Backend & Telegram Control System

نظام إدارة خوادم تطبيق **AHMED VPN** باستخدام **Python + Telegram Bot + FastAPI + SQLite**.

---

## 📁 هيكلية ملفات المشروع:
```
backend/
├── bot.py             # بوت إدارة التليجرام الخاص بالمالك (OWNER_ID: 6803988521)
├── api.py             # خادم REST API (FastAPI) لجلب وإدارة السيرفرات + الإعلانات + التحديث
├── database.py        # قاعدة بيانات SQLite (ahmed_vpn.db)
├── requirements.txt   # متطلبات التشغيل
├── .env.example       # نموذج لمتغيرات البيئة
├── .env               # ملف الإعدادات والتوكن السري
├── .gitignore         # تجاهل الملفات الحساسة
└── README.md          # دليل الاستخدام والتوثيق
```

---

## ⚙️ الإعداد والتشغيل السريع

### 1. تثبيت المتطلبات:
```bash
pip install -r requirements.txt
```

### 2. إعداد ملف `.env`:
```ini
BOT_TOKEN=ضع_توكن_البوت_هنا
OWNER_ID=6803988521
ADMIN_API_KEY=مفتاح_عشوائي_قوي_خاص_بك
HOST=0.0.0.0
PORT=8080
```
> ⚠️ **مهم:** غيّر قيمة `ADMIN_API_KEY` إلى مفتاح طويل عشوائي. لم يعد هناك مفتاح افتراضي داخل الكود،
> وإن لم تُضبط القيمة سترفض نقاط الإدارة (endpoints) العمل.

### 3. تشغيل النظام:
بأمر واحد فقط يتم تشغيل كل من **بوت التليجرام** و **سيرفر FastAPI**:
```bash
python bot.py
```
> أو لتشغيل الـ API بشكل منفصل باستخدام uvicorn:
> ```bash
> uvicorn api:app --host 0.0.0.0 --port 8080 --reload
> ```

---

## 🤖 مميزات بوت التليجرام (خاص بالمالك فقط):
- **حماية تامة:** المالك ذو الآيدي `6803988521` فقط من يمكنه استخدام اللوحة.
- **القائمة الرئيسية:**
  - `➕ إضافة سيرفر`: تدعم (VLESS, VMESS, TROJAN) بخطوات سهلة أو بلصق الرابط مباشرة.
  - `🗑️ مسح سيرفر`: قائمة بالسيرفرات مع تأكيد الحذف.
  - `📋 عرض السيرفرات`: عرض تفاصيل كل سيرفر.
  - `📢 إعلان للتطبيق`: إرسال إعلان يظهر كإشعار لكل المستخدمين داخل التطبيق.
  - `⬆️ تحديث إجباري`: تفعيل إشعار تحديث إجباري مع رابط تحميل الـAPK.
  - `🔄 تحديث`: تحديث إحصائيات اللوحة.

### أوامر سريعة:
- `/announce نص الإعلان`
- `/update versionCode apk_url [message]`

---

## 🌐 مسارات الـ API:

### مسارات التطبيق (عامة):
| الطريقة | المسار | الوصف |
|---|---|---|
| GET | `/api/servers` | جلب قائمة السيرفرات للتطبيق |
| GET | `/api/servers/{id}` | تفاصيل سيرفر واحد |
| GET | `/api/health` | فحص حالة النظام |
| GET | `/api/notifications` | آخر إعلان (يقرأه التطبيق دورياً) |
| GET | `/api/app-update` | بيانات التحديث الإجباري |
| GET | `/api/stats` | عدد المستخدمين لكل سيرفر |
| POST | `/api/user/ping` | تسجيل الجهاز/التثبيت |
| POST | `/api/user/activity` | تسجيل اتصال/فصل (لعدّ المستخدمين) |

### مسارات الإدارة (تتطلب الهيدر `X-API-Key: ADMIN_API_KEY`):
| الطريقة | المسار | الوصف |
|---|---|---|
| POST | `/api/servers` | إضافة سيرفر |
| DELETE | `/api/servers/{id}` | حذف سيرفر |
| POST | `/api/notifications` | إرسال إعلان جديد |
| POST | `/api/app-update` | ضبط التحديث الإجباري |

#### أمثلة:
```json
// POST /api/user/activity
{ "user_id": "dev-abc123", "server": "Germany 01", "event": "connect" }

// POST /api/app-update  (X-API-Key required)
{ "enabled": true, "version_code": 185, "url": "https://example.com/app.apk", "message": "نسخة جديدة" }
```

> ملاحظة: رابط الـ API الذي يستخدمه التطبيق هو `<host>/api/servers` (مشفّر داخل التطبيق عبر SecureVault)،
> وبقية النقاط تُبنى عليه تلقائياً (`/api/notifications`, `/api/stats`, ...).
