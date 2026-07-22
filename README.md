# 🐝 Swarm Agent System

> نظام سرب ذكي متعدد الوكلاء — ينافس أنظمة التفكير المتقدمة

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://python.org)
[![Tests 99/99](https://img.shields.io/badge/Tests-99%2F99-brightgreen.svg)](#الاختبارات)
[![License](https://img.shields.io/badge/License-MIT-orange.svg)](#)

---

## 📋 نظرة عامة

نظام سرب ذكي يتألف من **8 عمال متخصصين** يعملون بشكل تعاوني لحل مشكلات البرمجة المعقدة. النظام يجمع بين:

- **الذكاء الدستوري** — قواعد أخلاقية تمنع الكود الضار
- **الأنبوب الخفي للتفكير** — 6 مراحل تحليل قبل التنفيذ
- **نظام الميزانية التكيفي** — تخصيص التوكن حسب تعقيد المهمة
- **بروتوكول الذاكرة** — حفظ واسترجاع المعرفة بين الجلسات

---

## 🏗️ البنية التحتية

### العمال الثمانية

| العامل | الدور | النموذج |
|--------|-------|---------|
| 🔬 **Innovator** | ابتكار حلول إبداعية | DeepSeek V4 Flash |
| 🔍 **Critic** | مراجعة وانتقاد الكود | Nemotron 3 Nano 30B |
| 🏗️ **Architect** | تصميم البنية التحتية | Nemotron 3 Ultra |
| 🔎 **Explorer** | استكشاف وبحث الملفات | MiMo V2.5 |
| 📝 **Reviewer** | مراجعة UX والتصميم | Nemotron 3 Super |
| 🧠 **Reasoner** | تفكير منطقي عميق | Tencent Hy3 |
| 🎨 **Vision-Coder** | كود متعدد الوسائط | MiniMax M3 |
| ✅ **Swarm-Worker-QA** | اختبار وتحقق | nemotron-super |

### مراحل التفكير الستة

```
1️⃣ فهم المشكلة → 2️⃣ تحليل المدخلات → 3️⃣ توليد الأفكار
        ↓
4️⃣ تقييم البدائل ← 5️⃣ اختبار التخمين ← 6️⃣ صنع القرار
```

### الذكاء الدستوري

```
📌 المبدأ 1: لا تُدمّر — لا تحذف ملفات المستخدم بدون إذن
📌 المبدأ 2: لا تُخفي — كل قرار يحتاج مبرر واضح
📌 المبدأ 3: لا تتعمّد الخطأ — لا كود ي故意造成 مشاكل
📌 المبدأ 4: احترم الخصوصية — لا تسجل مفاتيح أو أسرار
📌 المبدأ 5: كن قابلاً للإلغاء — كل عملية يمكن التراجع عنها
```

---

## 📁 هيكل المشروع

```
swarm-agent/
├── opencode.json              # الإعدادات الرئيسية + السرب
├── vault_server.py            # خادم REST للمستودع (482 سطر)
├── skills/
│   ├── swarm-constitutional-layer/   # الذكاء الدستوري
│   ├── swarm-scratchpad/             # يافطة التفكير الخاصة
│   ├── swarm-token-budget/           # نظام ميزانية التوكن
│   ├── swarm-memory-protocol/        # بروتوكول الذاكرة
│   ├── swarm-observability/          # الرصد والمراقبة
│   └── swarm-worker-enhanced/        # 8 عمال متخصصين
│       ├── innovator/
│       ├── critic/
│       ├── architect/
│       ├── explorer/
│       ├── reviewer/
│       ├── reasoner/
│       ├── vision-coder/
│       └── swarm-worker-qa/
├── notes-api/                 # REST API بـ Flask (10 اختبارات)
├── user-service/              # خدمة مستخدمين + SQLite + Cache
├── db-migration/              # ترحيل قاعدة البيانات (38 اختبار)
├── self-improver/             # محلل ومحسن الكود (19 اختبار)
├── task-manager/              # أداة إدارة المهام
├── fastapi-rest-api/          # API كامل بـ FastAPI + JWT
├── factorial/                 # حل Factorial (6 اختبارات)
├── reverse_string/            # حل Reverse String (6 اختبارات)
├── calculator.py              # حل Calculator (6 اختبارات)
├── fibonacci.py               # حل Fibonacci
├── lcs.py                     # حل Longest Common Subsequence
└── string_utils/              # أدوات النصوص
```

---

## 🚀 التشغيل

### المتطلبات

```bash
# Python 3.13+
python3 --version

# تثبيت المكتبات
pip install flask fastapi uvicorn requests pytest
```

### تشغيل خادم الفولت

```bash
# تشغيل مباشر
python3 vault_server.py

# أو كـ systemd service
systemctl --user start vault-server.service
systemctl --user status vault-server.service
```

الخادم يعمل على `http://127.0.0.1:27123`

### اختبار الاتصال

```bash
# التحقق من صحة الخادم
curl -H "Authorization: Bearer swarm-evolution-2025" http://127.0.0.1:27123/

# قائمة الملفات
curl -H "Authorization: Bearer swarm-evolution-2025" http://127.0.0.1:27123/vault/

# البحث
curl -H "Authorization: Bearer swarm-evolution-2025" \
  "http://127.0.0.1:27123/search/simple/?query=swarm"
```

---

## 🧪 الاختبارات

### تشغيل كل الاختبارات

```bash
# اختبارات التحديات
pytest test_hello.py test_factorial.py test_reverse_string.py test_calculator.py -v

# اختبار Notes API
pytest notes-api/test_notes_api.py -v

# اختبار DB Migration
pytest db-migration/test_migration.py -v

# اختبار Self-Improver
pytest self-improver/test_self_improver.py -v
```

### نتائج الاختبارات

| المستوى | المهمة | النتيجة |
|---------|--------|---------|
| 🟢 سهل | Hello World | ✅ 3/3 |
| 🟢 سهل | Factorial | ✅ 6/6 |
| 🟢 سهل | Reverse String | ✅ 6/6 |
| 🟡 متوسط | Notes REST API | ✅ 10/10 |
| 🟠 صعب | User Service (API + DB + Cache) | ✅ 17/17 |
| 🔴 صعب جداً | DB Migration v1→v2 + Rollback | ✅ 38/38 |
| 💀 مستحيل | Self-Improving Code Optimizer | ✅ 19/19 |
| **المجموع** | | **99/99 ✅** |

---

## 🔌 خادم REST للمستودع

خادم REST متوافق مع `obsidian-mcp-server` — يوفر واجهة HTTP كاملة للمستودع.

### الـ Endpoints

| الطريقة | المسار | الوصف |
|---------|--------|-------|
| `GET` | `/` | معلومات الخادم |
| `GET` | `/health` | فحص الصحة |
| `GET` | `/vault/` | قائمة كل الملفات |
| `GET` | `/vault/{path}` | قراءة ملاحظة |
| `PUT` | `/vault/{path}` | إنشاء/تحديث ملاحظة |
| `PATCH` | `/vault/{path}` | تحديث جزئي |
| `DELETE` | `/vault/{path}` | حذف ملاحظة |
| `HEAD` | `/vault/{path}` | حجم الملاحظة |
| `GET` | `/tags/` | قائمة الوسوم |
| `GET` | `/search/` | بحث متقدم |
| `POST` | `/search/simple/` | بحث بسيط |
| `GET` | `/commands/` | أوامر Obsidian |
| `POST` | `/commands/{id}` | تنفيذ أمر |
| `GET` | `/periodic/{period}/` | ملاحظات دورية |

### الـ MCP Server

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "npx",
      "args": ["obsidian-mcp-server"],
      "env": {
        "OBSIDIAN_API_KEY": "swarm-evolution-2025",
        "OBSIDIAN_API_URL": "http://localhost:27123"
      }
    }
  }
}
```

**الأدوات المتاحة (12 أداة):**
- `obsidian_get_note` — قراءة ملاحظة
- `obsidian_create_note` — إنشاء ملاحظة
- `obsidian_update_note` — تحديث ملاحظة
- `obsidian_patch_note` — تحديث جزئي
- `obsidian_delete_note` — حذف ملاحظة
- `obsidian_search_notes` — بحث
- `obsidian_list_files` — قائمة الملفات
- `obsidian_list_tags` — قائمة الوسوم
- `obsidian_move_note` — نقل ملاحظة
- `obsidian_execute_command` — تنفيذ أمر
- `obsidian_open_file` — فتح ملف
- `obsidian_get_periodic_note` — ملاحظة دورية

---

## 🛠️ التقنيات

- **Python 3.13** — اللغة الأساسية
- **Flask** — خادم HTTP خفيف
- **FastAPI** — API سريع مع توثيق تلقائي
- **SQLite** — قاعدة البيانات
- **uvicorn** — خادم ASGI
- **pytest** — إطار الاختبار
- **Obsidian** — إدارة الملاحظات

---

## 📊 الموارد

- **1082+ مهارة** متاحة في النظام
- **92 مهارة** خاصة بالvault
- **8 عمال** متخصصين بنسخ مجانية
- **6 مراحل** تفكير عميق

---

## 📜 الترخيص

MIT License — свободен للاستخدام والتعديل.

---

## 🤝 المساهمة

1. Fork المشروع
2. أنشئ branch جديد (`git checkout -b feature/moujaddid`)
3. احفظ التغييرات (`git commit -m 'إضافة ميزة جديدة'`)
4. ادفع الـ branch (`git push origin feature/moujaddid`)
5. افتح Pull Request

---

## 📞 التواصل

- **GitHub:** [MohamedNamper333/swarm-agent](https://github.com/MohamedNamper333/swarm-agent)
- **Issues:** [افتح مشكلة](https://github.com/MohamedNamper333/swarm-agent/issues)

---

> **صُنع بـ ❤️ بواسطة Swarm Agent System**
