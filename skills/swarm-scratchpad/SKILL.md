# SWARM PRIVATE SCRATCHPAD
## كل عامل يكتب reasoning داخلياً — لا يظهر للمستخدم

### البروتوكول:

#### لكل Task مُرسَل لعامل:
```json
{
  "task": { ... },
  "scratchpad_protocol": {
    "enabled": true,
    "sections": [
      "problem_understanding",      // فهم المشكلة بلغته
      "assumptions_explicit",       // افتراضات صريحة
      "approach_options",           // خيارات الحل مع trade-offs
      "selected_approach",          // المختار + لماذا
      "risk_assessment",            // مخاطر + mitigation
      "falsification_test",         // كيف يثبت خطأه؟
      "confidence_level"            // 0-100%
    ],
    "format": "internal_monologue",  // لا يظهر للمستخدم
    "max_tokens": 2000              // ميزانية التفكير
  }
}
```

#### مخرجات العامل تصبح:
```json
{
  "result": "...",           // ما يراه المستخدم
  "scratchpad": {            // مخفي، للمراجعة فقط
    "problem_understanding": "...",
    "assumptions_explicit": [...],
    "approach_options": [...],
    "selected_approach": "...",
    "risk_assessment": [...],
    "falsification_test": "...",
    "confidence_level": 85
  }
}
```

---

### التكامل مع Ejentum Harness:

| مرحلة العمل | Harness مستخدم | الغرض |
|-------------|----------------|-------|
| **قبل** أي تنفيذ كود | `harness_code` | scaffold تنفيذ صحيح |
| **قبل** أي مراجعة/تقييم | `harness_anti_deception` | يمنع sycophancy |
| **قبل** أي تخطيط معقد | `harness_reasoning` | scaffold تفكير منظم |
| **بعد** كل مهمة | `harness_memory` | يكتشف drift عبر الجلسات |

### تنسيق استدعاء Harness:
```markdown
استدعي: `skill(name="ejentum-reasoning-harness")`
ثم: استخدم الـ tool المناسب:
- harness_code(prompt="...")
- harness_anti_deception(prompt="...")
- harness_reasoning(prompt="...")
- harness_memory(observation="...")
```

---

### مهارات داعمة:
- `ejentum-reasoning-harness` (العمود الفقري) — 679 عملية معرفية
- `thinking-systems` — تفكير منظومي
- `sequential-thinking` — خطوة بخطوة
- `thought-based-reasoning` — CoT متقدم
- `critical-thinking` — تحليل الحجج
- `thinking-metacognition` — تفكير في التفكير

---

### استخدام السرب:

```markdown
## في Stage 3 (High-Efficiency Execution):
- عند dispatch أي عامل → أرفق scratchpad_protocol في الـ prompt
- العامل يكتب scratchpad أولاً (داخلياً)
- ثم ينتج result
- السرب يستلم: result + scratchpad
- السرب يخزن: execution_log.md (result) + scratchpad_archive/ (scratchpad)

## في Stage 4 (Auto-Verdict):
- مراجعة scratchpad للتأكد من:
  - هل falsification_test نجح؟
  - هل confidence_level واقعي؟
  - هل assumptions_explicit مبررة؟
- إذا فشل → STOP، worker يعيد المحاولة
```