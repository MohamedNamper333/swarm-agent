# خطة الإصلاح الشاملة — 50-Agent Swarm Integration

**التاريخ**: 2026-08-12
**الحالة**: جاهز للتنفيذ
**المُنفذ**: Claude
**Commit الحالي**: `985416e`

---

## 📊 الوضع الحالي

| المقياس | القيمة |
|---------|--------|
| عدد الـ agents | 52 (Board 5 + C-Suite 7 + Code 7 + Design 8 + Video 6 + Research 4 + Data 3 + Language 3 + Knowledge 5 + Safety 4) |
| عدد الـ chains | 55 (52 + 3 inline safety) |
| عدد الـ models الفريدة | 55 |
| عدد الـ tests | 101 (كلها ناجحة) |
| إجمالي الـ LOC | 4176 (enterprise code) + 1583 (tests) |
| عدد الأقسام (silos) | 10 |
| **نسبة التكامل الحالي** | **~40%** |

---

## 🎯 الأهداف النهائية (Target State)

| المقياس | المستهدف |
|---------|----------|
| **نسبة التكامل** | 95%+ |
| **End-to-end workflow** | يعمل (Board → C-Suite → Dept → Worker) |
| **Safety Dept دقة** | 90%+ detection |
| **REST API coverage** | 100% للأقسام الـ 10 |
| **Tests** | 200+ اختبار |
| **Pass rate** | 100% |
| **Documentation** | محدثة لكل ملف جديد |

---

## 🏗️ الـ Architecture الجديد المقترح

```
                     SwarmMaster
                         |
        ┌────────────────┼────────────────┐
        |                |                |
     Board           C-Suite         SafetyDept
   (VETO check)    (CFO budget)    (PII/violence)
        |                |                |
        └────→ Executive Decision ←────┘
                         |
        ┌────────────────┼────────────────┐
        |                |                |
    Code Dept       Design Dept     Video Dept
    (7 agents)      (8 agents)      (6 agents)
        |                |                |
    ┌───┴───┐       ┌───┴───┐        ┌───┴───┐
    |       |       |       |        |       |
  coder  qa      image  3D      video  motion
```

**التدفق الجديد:**
1. **User Request** → POST `/swarm/process`
2. **SwarmMaster.process()** ينسق كل الأقسام
3. **SafetyDept** يفحص PII/violence أولاً (Block-on-veto)
4. **Board.deliberate()** → VETO check (ethics_advisor)
5. **C-Suite.executive_meeting()** → CFO budget, CLO legal VETO
6. **Route to Dept** حسب نوع المهمة
7. **Worker** ينفذ ويعيد النتيجة

---

## 📋 الخطة التنفيذية (4 Phases)

### Phase A: Core Integration Layer (أولوية قصوى)
**المدة المقدرة**: 2-3 ساعات
**عدد الملفات الجديدة**: 2
**عدد الاختبارات الجديدة**: 20+

#### A1. SwarmMaster Orchestrator
**الملف**: `swarm/enterprise/swarm_master.py` (~300 LOC)

```python
class SwarmMaster:
    """Coordinates all 50 agents in a unified workflow."""
    
    def __init__(self):
        # Core infrastructure (shared)
        self.executor = FallbackChainExecutor()
        self.safety = InlineSafetyFilter()
        self.cache = get_default_cache()
        self.rate_limiter = get_rate_limiter()
        self.circuit_breaker = get_circuit_breaker()
        
        # Safety Department (VETO-first)
        self.safety_dept = create_safety_dept()
        
        # Tier 1: Board (strategic decisions)
        self.board = create_board()
        
        # Tier 2: C-Suite (executive decisions)
        self.csuite = create_c_suite()
        
        # Tier 3: Departments (operational)
        self.depts = {
            'code': create_code_dept(),
            'design': create_design_dept(),
            'video': create_video_dept(),
            'research': create_research_dept(),
            'data': create_data_dept(),
            'language': create_language_dept(),
            'knowledge': create_knowledge_dept(),
            'safety': create_safety_dept(),
        }
    
    def process(self, request: Dict) -> Dict:
        """End-to-end workflow with VETO checks at every tier."""
        # 1. Safety Dept (PII/violence block)
        safety_check = self.safety_dept.full_check(str(request), use_llm=False)
        if safety_check.verdict.value in ('unsafe', 'critical'):
            return {'verdict': 'vetoed', 'vetoed_by': 'safety_dept', 'reason': safety_check.explanation}
        
        # 2. Board (strategic VETO)
        board_result = self.board.deliberate(request.get('question', str(request)))
        if board_result.vetoed_by:
            return {'verdict': 'vetoed', 'vetoed_by': board_result.vetoed_by, 'reason': board_result.veto_reason}
        
        # 3. C-Suite (executive decision)
        csuite_result = self.csuite.executive_meeting(request)
        if csuite_result['verdict'] == 'vetoed':
            return {'verdict': 'vetoed', 'vetoed_by': csuite_result['vetoed_by'], 'reason': csuite_result['reason']}
        
        # 4. Route to dept
        dept_name = self._route_to_dept(request)
        if dept_name:
            return self.depts[dept_name].run_agent(...)
        
        return {'verdict': 'approved', 'result': '...'}
```

**الاختبارات**: `tests/enterprise/test_swarm_master.py` (~200 LOC, 20+ tests)
- Safety VETO blocks PII
- Board VETO blocks unethical content
- C-Suite VETO blocks illegal/budget overflow
- Routing logic: code → Code Dept, design → Design Dept, etc.
- End-to-end Uber Eats scenario

#### A2. Smart Placeholder (Critical Fix)
**الملف**: `swarm/enterprise/core/placeholder.py` (~150 LOC)

```python
class SmartPlaceholder:
    """Realistic placeholder responses for dev/testing without API key."""
    
    def generate(self, model_id: str, prompt: str) -> Dict:
        model_type = self._classify_model(model_id)
        response = self._generate_by_type(model_type, prompt)
        return {
            'model': model_id,
            'prompt': prompt[:200],
            'response': response,
            'placeholder': True,
            'latency_ms': 50 + random.randint(0, 100),
        }
    
    def _classify_model(self, model_id: str) -> str:
        if 'nemotron' in model_id and 'ultra' in model_id:
            return 'reasoning'
        elif 'flux' in model_id:
            return 'image'
        elif 'cosmos' in model_id:
            return 'video'
        # ... etc
    
    def _generate_by_type(self, model_type: str, prompt: str) -> str:
        # Generate realistic response based on model type
        if model_type == 'reasoning':
            return f"Based on analysis of '{prompt[:100]}', I recommend..."
        elif model_type == 'code':
            return f"def solution():\n    # Implementation for: {prompt[:50]}\n    pass"
        # ...
```

**التكامل**: تعديل `FallbackChainExecutor` ليستخدم SmartPlaceholder بدلاً من dict الفارغ.

**الاختبارات**: 10+ tests لأنواع النماذج المختلفة.

---

### Phase B: Safety Department Hardening (أولوية عالية)
**المدة المقدرة**: 1-2 ساعة
**عدد الملفات المعدلة**: 2
**عدد الاختبارات الجديدة**: 15+

#### B1. Content Safety Regex Patterns
**الملف**: `swarm/enterprise/safety/__init__.py` (تعديل ~200 LOC)

```python
class ContentSafetyAnalyst(SafetyAgentBase):
    # Add real regex patterns for content safety
    CONTENT_PATTERNS = {
        # PII
        r'\b\d{3}-\d{2}-\d{4}\b': (Severity.CRITICAL, 'CWE-359', 'SSN detected'),
        r'\b\d{16}\b': (Severity.CRITICAL, 'CWE-359', 'Credit card number'),
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': (Severity.MEDIUM, 'CWE-359', 'Email address'),
        
        # Violence
        r'\b(kill|murder|assassinate|stab|shoot)\b.*\b(person|people|someone|them)\b': (Severity.CRITICAL, 'CWE-1004', 'Violence'),
        r'\b(bomb|explosive|detonate)\b': (Severity.HIGH, 'CWE-1004', 'Explosive content'),
        
        # Hate speech
        r'\b(racial slur|ethnic slur)\b': (Severity.CRITICAL, 'CWE-1004', 'Hate speech'),
        
        # Self-harm
        r'\b(suicide|self.harm|kill.myself)\b': (Severity.CRITICAL, 'CWE-1004', 'Self-harm'),
        
        # Illegal
        r'\b(drug trafficking|money laundering|tax evasion)\b': (Severity.HIGH, 'CWE-1004', 'Illegal activity'),
    }
    
    def quick_check(self, text: str) -> Optional[SafetyCheckResult]:
        """Regex-based content check (no LLM needed)."""
        text_lower = text.lower()
        for pattern, (sev, cwe, desc) in self.CONTENT_PATTERNS.items():
            if re.search(pattern, text_lower):
                return SafetyCheckResult(
                    stage='content_safety',
                    passed=False,
                    severity=sev.value,
                    message=f'{desc} ({cwe})',
                    model='regex',
                    latency_ms=0.001,
                )
        return None
```

#### B2. Topic Control Patterns
إضافة patterns للكشف عن off-topic content.

#### B3. Board ↔ Safety Integration
تعديل `Board.deliberate()` ليستدعي `SafetyDept.full_check()` قبل الـ LLM calls.

**الاختبارات**: 15+ tests لكشف PII, violence, hate speech, illegal content.

---

### Phase C: REST API Coverage (أولوية عالية)
**المدة المقدرة**: 2-3 ساعات
**عدد الملفات المعدلة**: 1 (`swarm/api/rest_server.py`)
**عدد الـ endpoints الجديدة**: 15+
**عدد الاختبارات**: 20+

#### C1. Department Endpoints
```python
# Board endpoints
@app.post("/board/deliberate")
async def board_deliberate(request: BoardRequest):
    return master.board.deliberate(request.question)

@app.get("/board/agents")
async def board_agents():
    return master.board.list_agents()

# C-Suite endpoints
@app.post("/csuite/meeting")
async def csuite_meeting(request: ProposalRequest):
    return master.csuite.executive_meeting(request.proposal)

@app.get("/csuite/budget")
async def csuite_budget():
    return master.csuite.cfo.get_status()

# Code dept endpoints
@app.post("/code/full-pipeline")
async def code_pipeline(request: CodeRequest):
    return master.depts['code'].full_pipeline(request.requirements)

@app.post("/code/review")
async def code_review(request: ReviewRequest):
    return master.depts['code'].review_only(request.code, request.language)

# Design dept endpoints
@app.post("/design/brand-kit")
async def design_brand_kit(request: BrandKitRequest):
    return master.depts['design'].generate_complete_brand_kit(request.brand_name)

@app.post("/design/image")
async def design_image(request: ImageRequest):
    return master.depts['design'].image_gen_1.generate(request.prompt)

# Video dept endpoints
@app.post("/video/promo")
async def video_promo(request: PromoRequest):
    return master.depts['video'].create_promo_video(request.brief)

# Research dept endpoints
@app.post("/research/full")
async def research_full(request: ResearchRequest):
    return master.depts['research'].full_research(request.query)

# Data dept endpoints
@app.post("/data/analyze")
async def data_analyze(request: DataQuestionRequest):
    return master.depts['data'].analyze_question(request.question)

# Language dept endpoints
@app.post("/language/translate")
async def language_translate(request: TranslationRequest):
    return master.depts['language'].translator.translate(
        request.text, request.source_lang, request.target_lang
    )

# Knowledge dept endpoints
@app.post("/knowledge/query")
async def knowledge_query(request: KnowledgeQueryRequest):
    return master.depts['knowledge'].query(request.question)

# Safety dept endpoints
@app.post("/safety/check")
async def safety_check(request: SafetyCheckRequest):
    return master.safety_dept.full_check(request.text, use_llm=request.use_llm)
```

#### C2. Master Endpoint
```python
@app.post("/swarm/process")
async def swarm_process(request: SwarmRequest):
    """End-to-end processing through all tiers."""
    return master.process(request.dict())
```

#### C3. Auth Bypass for Dev
```python
# Add dev mode to skip auth scopes
if os.environ.get("SWARM_DEV_MODE") == "true":
    # Skip auth for dev/testing
    pass
```

---

### Phase D: Integration Tests + End-to-End (أولوية متوسطة)
**المدة المقدرة**: 2-3 ساعات
**عدد الملفات**: 3
**عدد الاختبارات**: 30+

#### D1. SwarmMaster Tests
**الملف**: `tests/enterprise/test_swarm_master.py` (~300 LOC)
- Test Safety VETO blocks PII
- Test Board VETO blocks unethical
- Test C-Suite VETO blocks legal issues
- Test CFO budget circuit breaker
- Test routing logic for each dept
- Test end-to-end Uber Eats scenario

#### D2. Cross-Department Workflow Tests
**الملف**: `tests/enterprise/test_workflows.py` (~200 LOC)
- Test Board → Code workflow
- Test C-Suite → Design workflow
- Test Research → Knowledge → Board workflow

#### D3. End-to-End Scenario
**الملف**: `tests/enterprise/test_e2e_uber_eats.py` (~150 LOC)
```python
def test_uber_eats_full_flow():
    """Simulate: User orders food → Board approves → C-Suite budgets → Code builds app."""
    master = SwarmMaster()
    
    request = {
        'question': 'Build a food delivery app',
        'type': 'code',
        'estimated_cost': 50000,
    }
    
    result = master.process(request)
    assert result['verdict'] == 'approved'
    assert 'code' in result['executed_by']
```

#### D4. REST API Integration Tests
**الملف**: `tests/enterprise/test_rest_integration.py` (~200 LOC)
- Test كل endpoint جديد
- Test auth bypass in dev mode
- Test error handling

---

## 📅 الجدول الزمني

| Phase | الوصف | عدد الملفات | عدد الـ Tests | المدة |
|-------|------|-------------|--------------|------|
| Phase A | Core Integration (SwarmMaster + SmartPlaceholder) | 2 | 30+ | 2-3 ساعات |
| Phase B | Safety Hardening | 2 (modified) | 15+ | 1-2 ساعة |
| Phase C | REST API Coverage | 1 (modified) | 20+ | 2-3 ساعات |
| Phase D | Integration + E2E Tests | 3 | 30+ | 2-3 ساعات |
| **المجموع** | | **8** | **95+** | **7-11 ساعة** |

---

## 📊 معايير النجاح (Success Criteria)

| المعيار | المستهدف | طريقة القياس |
|---------|----------|--------------|
| SwarmMaster.process() يعمل | ✅ | test_swarm_master.py |
| Safety Dept يكتشف PII/violence | ✅ | 90%+ accuracy in tests |
| REST endpoints لكل قسم | 15+ endpoints | test_rest_integration.py |
| End-to-end Uber Eats | ✅ | test_e2e_uber_eats.py |
| All 196 tests pass | ✅ | pytest |
| No regression | ✅ | 101 existing tests still pass |
| Commit نظيف | ✅ | single commit per phase |

---

## 🔄 خطة الـ Commits

```
Phase A: `refactor: add SwarmMaster orchestrator + SmartPlaceholder`
Phase B: `fix: harden Safety Dept with real regex patterns`
Phase C: `feat: add REST endpoints for all 10 departments`
Phase D: `test: add 95+ integration + e2e tests`
```

---

## ⚠️ المخاطر والتحذيرات

1. **SmartPlaceholder complexity**: قد يصبح معقداً جداً إذا حاول تقليد كل نموذج
   - **التخفيف**: ابدأ بـ 5 أنواع رئيسية فقط (reasoning, code, image, video, text)

2. **REST endpoints breaking changes**: قد تكسر الـ endpoints الموجودة
   - **التخفيف**: إضافة endpoints جديدة بدون حذف القديمة

3. **Safety regex false positives**: قد تحظر محتوى شرعي
   - **التخفيف**: patterns دقيقة مع word-boundary، اختبارات متنوعة

4. **Performance**: كل tier check يضيف latency
   - **التخفيف**: cache results, parallel execution where possible

---

## 🚀 الخطوة التالية

**ابدأ بـ Phase A** (الأكثر أهمية):
1. إنشاء `SwarmMaster` orchestrator
2. إنشاء `SmartPlaceholder` للـ fallback responses
3. اختبارات SwarmMaster (20+ tests)
4. Commit Phase A

**هل أنت جاهز للبدء بـ Phase A؟**
