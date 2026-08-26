# سجل التدقيق المؤسسي — LEDGER
تتبع ملف-بملف وفق IARP v1.0 | آخر تحديث: 2026-08-25

الحالات: ⬜ لم يُدقق | 🟡 محلل (A منجز) | 🔧 مُصلح (B) | ✅ مُحقق ومغلق (C+D)

## T1 — المسار الحرج ✅

| الملف/الوحدة | الحالة | تقرير |
|--------------|--------|-------|
| `enterprise/swarm_master.py` | ✅ | إعادة كتابة كاملة؛ ServiceAccessor، تهيئة 7 خصائص، pipeline سليم، عقود قديمة بمحوّلات |
| `core/model_registry.py` | ✅ | استبدال نماذج Zen الميتة (lightning/hy3) |
| `enterprise/core/model_registry_v2.py` | ✅ | 57 chain كلها نماذج حية مثبتة |
| `integrations/nvidia_nim.py` | ✅ | timeout kwarg قاتل + per-request timeout |
| `core/fallback_chain.py` | ✅ | restricted profiles ربط + placeholder صامت → fail-closed |
| `api/auth/*` (package) | ✅ | فك الحجب، secret محفوظ، atomic save، compare_digest، throttling |
| `api/rest_server.py` | ✅ | يستورد ✓ + بوابة مصادقة عامة secure-by-default |
| `enterprise/board/__init__.py` | ✅ | create_board حقيقي، أدوار registry، ethics gate حتمي، tiebreak/run_agent، dual-mode deliberate |
| `core/orchestration/components.py` | ✅ | استيرادات ناقصة، EvaluationContext schema، async توافقية |
| `plane/execution_plane.py` | ✅ | executor_registry crash |
| `safety/__init__.py` | ✅ | regex fail-open للمحتوى السليم (كان يرفض الكل بلا API key) |

## T2 — الأمني

| الملف/الوحدة | الحالة | تقرير |
|--------------|--------|-------|
| `execution/sandbox.py` | ✅ | S1–S8: seccomp مقيد، preexec fail-closed، traversal، symlink O_NOFOLLOW، tmpdir، مترجمات |
| `idempotency/store.py` | ✅ | I1–I6: tenant scoping، expiry، lease takeover، حفظ الأصل عند تعارض، retry-after-fail |
| `core/placeholder/*` (package) | ✅ | فك الحجب الثاني |
| `resilience/rate_limiter_v2.py` | ✅ | +RPM sliding window، attempt-accounting عند acquire، acquire_ex بأسباب (H1)، قفل كامل للـ reset، جداول مزامنة الكتالوج الحي |
| `core/fallback_chain.py` (بوابة الـ RL) | ✅ | reason-aware: daily→عقوبة، rpm→انتظار قصير، concurrent→لا تسمّم |
| `resilience/circuit_breaker.py` | ✅ | N1 HALF_OPEN ميت→مسار تعافٍ حقيقي؛ N2 rollover ذاتي (كان reset_daily بلا مستدعين)؛ N3 فتح عند 100% بدل 80% (إنقاذ 20% حصة)؛ drain() لاستعادة الطابور |
| `resilience/recovery_engine.py` | ✅ | H5 timezone ✓؛ M4a cycles→ValueError صريح؛ M4b قفل استعادة عام؛ سجل مقصوص 500؛ avg على الناجحين؛ singleton آمن |
| `snapshots/snapshot_manager.py` | ✅ | H6: checksum للملف المخزن + فحص حقيقي عند الاستعادة (تلاعب→CORRUPTED)؛ فهرس ذري + حجر صحيحة؛ INCREMENTAL يرفض بصدق |
| `budget/tracker.py` | ✅ | C4: transfer ينقل LIMIT (حفظ الطاقة، لا رصيد من العدم) + حارس obligations؛ M6/N-B1: رفض غير الموجب في spend/allocate؛ N-B2: CLOSED ترفض؛ N-B3: whitelist للـ updates؛ N-B8: EXCEEDED يُصل الآن؛ N-B9: سجل مقصوص + تنبيهات خارج القفل |
| `auth/rbac/engine.py` | ✅ | RB-N1 asyncio.run داخل loop→ميت؛ RB-N2 create_flag مكرر؛ N9 تجاهل tenant؛ انتهاء الصلاحية لم يكن يُفحص؛ N5 مفتاح كاش بلا attributes (تخطي)؛ N6 TTL مهمل؛ N4 listeners تحت قفل؛ N8 تكرار تعيين؛ N12 deploy كاذب |
| `policy/engine.py` | 🟡 | مستخدم في safety gate ✓؛ تدقيق كامل متبقٍ (764 سطر) |
| `execution/sandboxes/{gvisor,firecracker,network_enforcement,fs_enforcement}.py` | ⬜ | لم تُدقق (2000+ سطر) |

## T3 — البيانات

| الملف/الوحدة | الحالة | تقرير |
|--------------|--------|-------|
| `memory/v2/repository.py` | ✅ | نسخة الـ fallback الفاسدة (InMemory-style داخل Redis class) استُئصلت؛ تعقيم حقن FT.SEARCH (#26) |
| `persistence/locks.py` | 🟡 | timedelta ✓؛ تبقى RW-lock شكلي، semaphore دائم القبول، meta_key خاطئ |
| `state/manager.py` | 🟡 | acquire_lock مُصلح جذرياً: set_if_absent(NX) + حذف عند الإفراج + تحمّل None — 4 اختبارات عدائية ✓؛ يتبقى commit الذري |
| `persistence/consensus.py` (Raft) | ✅(معطّل) | بوابة أمان: مرفوض افتراضياً (split-brain أسوأ من لا-consensus)؛ تجاوز صريح بـ SWARM_ENABLE_UNSAFE_RAFT=1 |
| `memory/v2/lifecycle.py` | ✅ | return المفقودة أعادت دورة الأرشفة للحياة؛ إزالة ابتلاع CancelledError ×4 |
| `memory/v2/lessons.py` | ✅ | supersede؛ episode IDs فريدة + get_episode metadata-query؛ apply_lesson وrecord_lesson_outcome كلاهما CAS+retry ضد lost-updates |
| `memory/v2/search.py` | ✅ | to_thread لكل نداءات العميل المتزامن؛ إصلاح clobber المتغير؛ هروب قيم الفلاتر (حقن cross-tenant)؛ _wait_for_task لا يموّه أخطاء حقيقية |
| `core/memory_engine.py` | ✅(صادق) | الستَبز الزائفة (True/[]) → NotImplementedError صريح؛ التوجيه للمسار الحقيقي memory.v2 |
| `checkpoint_store.py` | ✅(جزئي) | rollback تعويضي مُثبت بحقن عطل؛ TTL يصل عبر schema الإصلاح السابق |
| `memory/v2/repository.py` (batch) | ✅ | إعادة كتابة BATCH script: flat-schema + تحقق الكل قبل كتابة أي (all-or-nothing) + ترجمة ResponseError الحقيقية بدل dead-code |

## T4 — الدعم (مسح مخاطر + إصلاحات أولى)

| الملف | الحالة | ملاحظات |
|-------|--------|---------|
| مسح مخاطر ثابت شجري | ✅ | 9 أنماط × كل T4 → قائمة مرتبة؛ إيجابيات كاذبة موثقة (eval/exec داخل SecurityChecker، "SQL" نصوص سجل، secrets.token_urlsafe) |
| `core/auto_verdict.py` | ✅(جزئي) | 5 bare-except→مسجلة؛ فاحصا Integration/CodeQuality كانا no-op يعيدان الدرجة الكاملة → stub معلن بسقف درجة |
| `job/compensation.py` | ✅(جزئي) | 6× persistence fire-and-forget: create_task بلا مرجع (GC hazard) + إسقاط صامت بلا loop → `_persist_state()` مركزية بخيوط آمنة وتسجيل؛ read-path تسجيل |
| نمو غير محدود (أكبر 3) | ✅ | self_reflection 200/agent · tracing queue 10k · metric points 5k |
| `plugins/loader.py` | ✅ | on_shutdown swallow-pass → مسجل (إلغاء التحميل لا يعلق لكنه لا يصمت) |
| `constitutional/*`, `context_manager/*` | ✅ | حزم فارغة مشروعة (re-export عبر intelligence) — لا كود ميت |
| `websocket_server.py` | ✅ | 14 طابعاً زمنياً naive → UTC-aware |
| نمو غير محدود (الدفعة الثانية) | ✅ | constitutional_audit 5k · compaction_history 2k · skill_discovery 5k · constitutional_guard 5k · inter_agent_bus 10k — كلها مقصوصة |
| `artifact/store.py` | ✅(جزئي) | AR-N1 🔴: traversal قراءة/كتابة على كل الجهاز (realpath guard)؛ N2: checksum_verified كان يُختم بلا تحقق → verify-after-write مع حذف الفاسد؛ N3: non-seekable buffering؛ N4: whitelist للـ updates |
| `servicemesh/server.py` | ✅(جزئي) | N3: ttl الممرر كان يُتجاهل (كل الشهادات 24h)؛ N1: revoke كان حذفاً كاذباً → حالة revoked + is_serial_revoked؛ N2: لا مفاتيح خاصة في الذاكرة الدائمة؛ N5: get_certificate كان pass→None (تنفيذ حقيقي عبر CA)؛ KeyUsage ناقص الحقول انهار الإصدار |
| `gateway/server.py` | ✅(جزئي) | CircuitState مكرر أزيل؛ token bucket: float tokens (كان int() يقصّ ويجوّع المنخفض المعدل) + الإنشاء يستهلك توكناً (منحة مجانية) + دلاء مقيدة 50k مع إخلاء خامول |
| `routing/service.py` | ✅(جزئي) | fallback الازدحام: saturated-but-healthy تُعاد بدل فشل التوجيه الكلي تحت الحمل (مُثبت)؛ دلالات strict-probe للقاطع موثقة؛ الموازنات السبع سليمة |
| `governance/service.py` | ✅(جزئي) | مقيّم تعبيرات آمن جديد (بدون eval): dotted-paths مع flat-fallback، and/or/not، مقارنات — سياسات الافتراضيات تشتغل فعلياً؛ ظل eval المدمج رفع؛ ALLOW لم يعد يُحسب مخالفة؛ سجل تدقيق مقصود 50k |



⬜ routing/service · governance · gateway · servicemesh · artifact/signing+store · observability/* · plugins · skill_discovery · reflections · intelligence · context_manager · constitutional · api/websocket_server · enterprise/departments الباقية (code/design/video/research/data/language/knowledge/csuite — أُنشئت وتعمل عبر master لكن لم تُدقق سطر-سطر)

## T5 — محاذاة الاختبارات

| البند | الحالة |
|-------|--------|
| `chaos_tests/test_chaos.py` SyntaxError سطر 273 | ✅ | قوس غير مغلق + success مكرر + uuidv7 مفقود → **10 تجارب تُحمَّل** |
| `tests/e2e/test_vault_integration` ImportError | ✅ | الوحدة حُذفت عمداً في a88175e → importorskip موثق بدل تسميم الـ collection |
| مسح A1 شجري: import كل الوحدات | ✅ | **220/220 تستورد نظيفاً** (كانت 4 فاشلة: sso Tuple، tokens حجب، contracts أسماء وهمية+IExecutionClient مكرر) |
| مسح A2 شجري: حجب وحدة/حزمة | ✅ | الحالة الثالثة artifact/signing مُصلحة بنمط إعادة التصدير؛ لا ظل متبقٍ |
| test_rbac_property (dpop/mtls) — pre-existing | ⬜ خارج النطاق (crypto بيئة) |
| test_workflows الـ6 المعتمدة على NIM quota | ⬜ تُشغل عند تجدد الحصة |
| e2e/test_vault_integration import | ⬜ |

---

**إحصائية:** ✅ مغلق: 14 وحدة حرجة | 🟡 جزئي: 4 | ⬜ متبقٍ: ~45 ملفاً أساسياً + دعم
