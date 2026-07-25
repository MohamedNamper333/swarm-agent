# AL-MUKH — نظام المزامنة والبحث المركزي لـ Obsidian Vaults

## نظرة عامة

**AL-MUKH** (المخ) هو نظام **Hub-and-Spoke** متكامل يربط مخزن Obsidian مركزي (Hub) بـ 50+ مخازن فرعية (Spokes) مع:
- **مزامنة حقيقية** (Real-time sync) عبر مراقب نظام الملفات (Watchdog)
- **بحث موحد** (Unified search) مدعوم بـ Meilisearch مع دعم كامل للعربية
- **روابط عابرة** (Cross-vault links) عبر نظام `[[namespace:path]]`
- **أمان مدمج** — مسح الأسرار، الصلاحيات، .gitignore
- **لوحة تحكم** — DASHBOARD.md + MAP.md + MOCs تلقائية

---

## البنية المعمارية (Architecture)

```
┌─────────────────────────────────────────────────────────────────┐
│                        AL-MUKH HUB                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Indexer    │  │  Watcher    │  │  Dashboard  │             │
│  │  (Queue)    │  │  (FS)       │  │  Generator  │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         ▼                ▼                ▼                     │
│  ┌─────────────────────────────────────────────────┐           │
│  │           Meilisearch (mukh-unified)            │           │
│  │   - ArabicAnalyzer | Smart ranking | Facets     │           │
│  └─────────────────────────────────────────────────┘           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
    ┌─────────┐       ┌─────────┐       ┌─────────┐
    │ Spoke 1 │       │ Spoke 2 │  ...  │ Spoke N │
    │ proj-*  │       │ research│       │ area-*  │
    └─────────┘       └─────────┘       └─────────┘
```

### المكونات الأساسية (Core Components)

| المكون | الملف | الوظيفة | المنفذ |
|---|---|---|---|
| **Vault REST Server** | `vault_server.py` | API للوصول للملفات (CRUD، بحث، وسوم) | 27123 |
| **Indexer** | `indexer.py` | فهرسة، طابور SQLite، لقطات (snapshots) | — |
| **Watcher** | `watcher.py` | مراقبة نظام الملفات (Watchdog)، صحة (health) | 8765 |
| **Dashboard** | `dashboard.py` | توليد DASHBOARD.md، MAP.md، MOCs | — |
| **Resolver** | `resolver.py` | تحليل الروابط `[[namespace:path]]` | — |
| **Namespace Resolver** | `namespace_resolver.py` | تحقق الأسماء، بادئات، محجوزات | — |
| **Symlink Manager** | `symlink_manager.py` | إدارة الروابط الرمزية للمخازن الفرعية | — |
| **Security** | `security.py` | مسح الأسرار، صلاحيات، .gitignore، .env | — |
| **Validator** | `validator.py` | فحوصات صحة النظام (قرص، Meili، pings) | — |
| **Config** | `config.py` | تحميل `.env` مركزي، إعدادات مشتركة | — |

---

## تدفق البيانات (Data Flow)

### 1. الفهرسة الأولية (Initial Indexing)
```bash
python indexer.py --full-scan
```
- يمسح جميع الملفات في `VAULT_ROOT` و `SPOKE_ROOTS`
- يستخرج: المحتوى، الوسوم (`#tag`)، الروابط `[[wiki]]`، العناوين، الهاش
- يرسل إلى Meilisearch بحزم (batches)
- يحفظ نقطة تفتيش (checkpoint) للاستئناف

### 2. المزامنة الحقيقية (Real-time Sync)
```
File Change (create/modify/delete/move)
        │
        ▼
   Watchdog Event
        │
        ▼
  Watcher Handler (debounce 500ms)
        │
        ▼
  IndexerQueue.enqueue(op, path, doc_id, content)
        │
        ▼
  Worker Thread → MeiliIndexer.index_file()
        │
        ▼
  Meilisearch (update/add/delete document)
        │
        ▼
  IndexerQueue.mark_done([queue_ids])
```

### 3. البحث (Search)
```
User Query → Meilisearch /indexes/mukh-unified/search
                    │
                    ▼
         ArabicAnalyzer (tokenization + normalization)
                    │
                    ▼
         Smart Ranking (typo-tolerance, proximity, attributes)
                    │
                    ▼
         Results with highlights, facets, filters
```

### 4. الروابط العابرة (Cross-vault Links)
```
[[proj-myproject:notes/meeting]] 
        │
        ▼
   Resolver.parse() → {ns: "proj-myproject", path: "notes/meeting"}
        │
        ▼
   NamespaceResolver.validate_name("proj-myproject")
        │
        ▼
   SymlinkManager.resolve_link(ns, path) → absolute_path
        │
        ▼
   Vault Server GET /vault/read?path=...
```

---

## إعداد البيئة (Environment Setup)

### المتغيرات المطلوبة (`.env`)
```bash
# Meilisearch
MEILI_URL=http://127.0.0.1:7700
MEILI_MASTER_KEY=0d2a487fedd74eda8118d12b492ae1469dc40c31a1cd25798730b0033b5bd389

# Vault
VAULT_ROOT=/home/kali/Documents/Obsidian Vault
VAULT_API_KEY=swarm-evolution-2025
```

### الخدمات (Systemd)
```bash
# Vault Server (user service)
systemctl --user enable --now vault-server.service
systemctl --user status vault-server.service
systemctl --user logs -f vault-server.service

# Meilisearch (Docker)
docker compose -f docker-compose.yml up -d
docker compose -f docker-compose.yml logs -f meilisearch
```

---

## واجهات البرمجة (API Reference)

### Vault Server (`http://127.0.0.1:27123`)

| Endpoint | Method | وصف |
|---|---|---|
| `/health` | GET | فحص الصحة |
| `/vault/list` | GET | قائمة الملفات مع فلترة |
| `/vault/read` | GET | قراءة ملف (مع frontmatter) |
| `/vault/write` | POST | كتابة/تحديث ملف |
| `/vault/delete` | DELETE | حذف ملف |
| `/vault/search` | GET | بحث نصي بسيط |
| `/vault/tags` | GET | استخراج جميع الوسوم |
| `/vault/backlinks` | GET | الروابط العكسية لملف |
| `/vault/frontmatter` | GET/POST | قراءة/كتابة frontmatter |

**المصادقة:** Header `X-API-Key: swarm-evolution-2025`

### Meilisearch (`http://127.0.0.1:7700`)

| Endpoint | Method | وصف |
|---|---|---|
| `/health` | GET | حالة المحرك |
| `/indexes/mukh-unified/search` | POST | بحث متقدم |
| `/indexes/mukh-unified/documents` | POST/GET | إضافة/جلب مستندات |
| `/indexes/mukh-unified/stats` | GET | إحصائيات الفهرس |

---

## نموذج المستند في Meilisearch (Document Schema)

```json
{
  "id": "proj-myproject:notes/meeting.md",
  "namespace": "proj-myproject",
  "path": "notes/meeting.md",
  "title": "Meeting Notes",
  "content": "محتوى الملف الكامل...",
  "content_hash": "a1b2c3d4e5f6...",
  "tags": ["meeting", "project", "arabic"],
  "links": ["[[proj-other:ref]]", "[[area-personal:todo]]"],
  "headings": ["# Meeting", "## Agenda", "## Decisions"],
  "frontmatter": {"date": "2026-07-25", "author": "user"},
  "size": 2048,
  "modified": "2026-07-25T14:30:00Z",
  "indexed_at": "2026-07-25T14:30:05Z"
}
```

**المفتاح الأساسي (Primary Key):** `id` = `namespace:path`

**إعدادات العربية (Arabic Settings):**
- `searchableAttributes`: `["title", "content", "tags", "headings"]`
- `filterableAttributes`: `["namespace", "tags", "path"]`
- `sortableAttributes`: `["modified", "size"]`
- `rankingRules`: الكلمات، السمات، الدقة، القرب، الترتيب

---

## الاختبارات (Testing)

### مجموعات الاختبارات
```bash
# اختبارات المراحل 2 (الأساسية)
python test_phase2.py        # 28/28 ✅

# اختبارات المراحل 3-5 (التكامل)
python test_phase345.py      # 22/22 ✅

# اختبارات الحالات الحدية (Edge Cases)
python test_edge_cases.py    # 88/88 ✅

# المجموع: 138/138 ✅
```

### ما تغطيه اختبارات Edge Cases
| المكون | الاختبارات |
|---|---|
| Indexer | ملفات فارغة، كبيرة (>1MB)، عربية، يونيكود، ثنائية، هاش، دفعات، طابور |
| Resolver | روابط صحيحة/خاطئة/فارغة/معيبة |
| Namespace | أسماء صحيحة/مخزنة/حدود/محجوزات (15 نمط) |
| Symlink | تسجيل/إلغاء/إنشاء/فحص روابط معطوبة |
| Security | مسح كامل، أسرار، صلاحيات، .gitignore، .env |
| Validator | فحوصات عامة/محددة/غير معروفة، أنواع النتائج |
| Dashboard | توليد، وجود الملفات، محتوى |
| Content Hash | حتمية، اختلاف، عربي، طول |
| Watcher | إعدادات (recursive، exclude، debounce) |
| Meilisearch | صحة، إحصائيات، مستندات، بحث عربي |

---

## الأمان (Security)

### مسح الأسرار (Secret Scanning)
```python
from security import scan_secrets_in_files, run_full_scan

# مسح ملفات محددة
findings = scan_secrets_in_files(["/path/to/vault"])

# مسح شامل
report = run_full_scan(vault_root="/home/kali/AL-MUKH")
```
**الأنماط المكتشفة:** API keys، tokens، passwords، private keys، database URLs، إلخ.

### فحوصات أخرى
- **الصلاحيات:** ملفات قابلة للكتابة من الجميع
- **.gitignore:** أنماط مفقودة (.env، *.key، secrets/)
- **.env مكشوفة:** ملفات .env في المسار
- **الكود:** بيانات اعتماد في ملفات Python/JS/Go

---

## استكشاف الأخطاء (Troubleshooting)

| المشكلة | السبب المحتمل | الحل |
|---|---|---|
| `MEILI_KEY` خاطئ | `.env` غير محمل | تحقق من `config.py`، تأكد من وجود `.env` |
| الفهرسة بطيئة | دفعات كبيرة | قلل `BATCH_SIZE` في `indexer.py` |
| Watcher لا يرسل | Debounce عالي | عدل `debounce_ms` في config.yaml |
| بحث عربي لا يعمل |Analyzer مفقود | تأكد من `ArabicAnalyzer` في إعدادات الفهرس |
| Vault Server 401 | API Key خاطئ | تحقق من `VAULT_API_KEY` في `.env` والنظام |
| Queue عالقة | `processing` state | `IndexerQueue.mark_done()` بعد المعالجة |

### أوامر التشخيص
```bash
# حالة Meilisearch
curl http://127.0.0.1:7700/health

# إحصائيات الفهرس
curl -H "Authorization: Bearer $MEILI_MASTER_KEY" \
  http://127.0.0.1:7700/indexes/mukh-unified/stats

# اختبار بحث
curl -X POST -H "Authorization: Bearer $MEILI_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q": "اجتماع", "limit": 5}' \
  http://127.0.0.1:7700/indexes/mukh-unified/search

# صحة Watcher
curl http://127.0.0.1:8765/health

# حالة Vault Server
curl -H "X-API-Key: swarm-evolution-2025" \
  http://127.0.0.1:27123/health
```

---

## الصيانة (Maintenance)

### لقطات (Snapshots)
```bash
# إنشاء لقطة يدوياً
python indexer.py --snapshot

# استعادة من لقطة
python indexer.py --restore search/snapshots/mukh_snapshot_20260725_143000.json
```

### تنظيف الطابور
```python
from indexer import IndexerQueue
queue = IndexerQueue()
queue.cleanup_stale(timeout_seconds=3600)  # عناصر معلقة > ساعة
```

### مراقبة القرص
```bash
# عبر Dashboard
python dashboard.py disk

# أو Validator
python validator.py --check disk
```

---

## التطوير المستقبلي (Roadmap)

| الميزة | الحالة | أولوية |
|---|---|---|
| MCP Integration | مخطط | عالية |
| Vector Search (embeddings) | بحث | متوسطة |
| Conflict Resolution (sync conflicts) | تصميم | عالية |
| Multi-user / Permissions | مخطط | متوسطة |
| Plugin Obsidian رسمي | بحث | منخفضة |
| Web UI للوحة التحكم | تصميم | متوسطة |
| Backup/Restore آلي | مخطط | عالية |

---

## الملفات الرئيسية (Key Files)

```
/home/kali/AL-MUKH/
├── config.py              # إعدادات مركزي (.env loader)
├── indexer.py             # الفهرس + الطابور + اللقطات
├── watcher.py             # مراقب نظام الملفات
├── dashboard.py           # مولد التقارير
├── resolver.py            # محلل الروابط
├── namespace_resolver.py  # مدقق الأسماء
├── symlink_manager.py     # مدير الروابط الرمزية
├── security.py            # الماسح الأمني
├── validator.py           # فحوصات الصحة
├── content_hash.py        # دالة الهاش (داخل indexer)
├── test_phase2.py         # اختبارات المرحلة 2
├── test_phase345.py       # اختبارات المراحل 3-5
├── test_edge_cases.py     # اختبارات الحالات الحدية
├── config.yaml            # إعدادات YAML
├── .env                   # أسرار البيئة
├── docker-compose.yml     # Meilisearch + Redis
├── DASHBOARD.md           # لوحة التحكم المولدة
├── index/MAP.md           # خريطة الفهرس
├── index/*.md             # MOCs لكل namespace
└── search/snapshots/      # لقطات الفهرس
```

---

## روابط مفيدة

- **GitHub:** https://github.com/MohamedNamper333/swarm-agent
- **Meilisearch Docs:** https://www.meilisearch.com/docs
- **Watchdog Docs:** https://python-watchdog.readthedocs.io
- **Obsidian API:** https://github.com/obsidianmd/obsidian-api

---

*آخر تحديث: 2026-07-25 | الإصدار: 2.1 | إجمالي الاختبارات: 138/138 ✅*