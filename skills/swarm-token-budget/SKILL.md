# SWARM TOKEN BUDGET MANAGER
## قرار ديناميكي: LITE (3 stages) vs STANDARD (4 stages) vs FULL (6 stages)

### خوارزمية القرار (في أول 30 ثانية):

```python
def decide_pipeline(task, context):
    complexity_score = 0
    
    # عوامل التعقيد (0-10 لكل منها)
    factors = {
        "unknown_unknowns": assess_unknowns(task),        # كم مجهول؟
        "irreversibility": assess_irreversibility(task),   # قرارات لا ترجع؟
        "stakeholder_count": count_stakeholders(task),     # كم صاحب مصلحة؟
        "technical_novelty": assess_novelty(task),         # تقنية جديدة؟
        "regulatory_risk": assess_compliance(task),        # مخاطر قانونية؟
        "blast_radius": assess_blast_radius(task),         # نطاق التأثير؟
    }
    
    complexity_score = sum(factors.values()) / 60 * 100  # 0-100
    
    # تسجيل القرار للتدقيق
    log_pipeline_decision({
        "task": task.summary,
        "factors": factors,
        "complexity_score": complexity_score,
        "selected_pipeline": get_pipeline_name(complexity_score),
        "timestamp": now()
    })
    
    if complexity_score < 30:
        return "LITE"       # 3 stages: Plan → Execute → Verify
    elif complexity_score < 60:
        return "STANDARD"   # 4 stages: + Design
    else:
        return "FULL"       # 6 stages الكامل
```

---

### LITE Pipeline (3 Stages) — للمهام البسيطة (< 30):
```
Stage 1: QUICK PLAN (5 min)      → strategic_plan.md (مختصر)
Stage 2: EXECUTE (parallel)      → workers dispatch
Stage 3: VERIFY & HANDOFF        → quality_report.md
Total: ~15-30 min
```
**Quality Gate إلزامي حتى في LITE:** structural + functional + integration checks

---

### STANDARD Pipeline (4 Stages) — للمهام المتوسطة (30-60):
```
Stage 1: STRATEGIC PLAN
Stage 2: DESIGN SPEC (Architecture)
Stage 3: EXECUTE
Stage 4: VERIFY & HANDOFF
Total: ~30-60 min
```

---

### FULL Pipeline (6 Stages) — للمهام المعقدة/الحرجة (> 60):
```
الـ 6 stages الحالية كاملة
Total: ~60-120+ min
```

---

### التبديل الديناميكي:

| السيناريو | الإجراء |
|------------|---------|
| اكتشف في Stage 2 أن المهمة أعقد | **UPGRADE إلى FULL** — أضف stages 2-5 المفقودة |
| Stage 1 يظهر بساطة شديدة | **DOWNGRADE إلى LITE** — اسحب design spec، ابدأ execute مباشرة |
| Worker يفشل متكرراً | **ESCALATE** — human decision على pipeline |

**قرار التبديل يسجل في:** `pipeline_decision_log.md`

---

### ميزانية التوكنز لكل Pipeline:

| Pipeline | Prompt Tokens | Context Budget | Max Task Time |
|----------|--------------|----------------|---------------|
| LITE | ~2,500 | ~4,000 | 30 min |
| STANDARD | ~4,000 | ~6,000 | 60 min |
| FULL | ~6,000 | ~10,000 | 120+ min |

---

### مهارات داعمة:
- `gstack-plan-tune` — self-tuning question sensitivity
- `strategic-compact` — manual context compaction
- `context-engineering` — context optimization
- `hierarchical-agent-memory` — scoped memory

---

### استخدام السرب:

```markdown
## في بداية أي مهمة (قبل Stage 1):
1. استدعي: `skill(name="swarm-token-budget")`
2. شغل: `decide_pipeline(task, context)`
3. النتيجة: "LITE" / "STANDARD" / "FULL"
4. سجل القرار في pipeline_decision_log.md
5. فعّل الـ pipeline المناسب

## في Stage 1 (Strategic Planning):
- إذا LITE: strategic_plan.md مختصر (صفحة واحدة)
- إذا STANDARD/FULL: strategic_plan.md كامل

## التبديل الديناميكي:
- مراقبة: complexity indicators أثناء العمل
- إذا تغير التقدير: سجل التبديل، فعّل pipeline الجديد
```