"""
قسم المعرفة — 5 وكلاء

الوكلاء:
- knowledge_director: مدير المعرفة، ينسق عمليات البحث والاسترجاع
- knowledge_curator: أمين المعرفة، يصنف ويقيّم جودة المعلومات
- knowledge_retriever: مسترجع RAG، يبحث في قاعدة المتجهات
- knowledge_reranker: معيد الترتيب، يحسن نتائج البحث
- knowledge_doc_parser: محلل المستندات، يستخرج النصوص من PDFs/HTML/etc

كل وكيل يستخدم سلسلة الاحتياط مع نماذجه المخصصة.
"""
import hashlib
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from swarm.enterprise.core.fallback_chain import FallbackChainExecutor
from swarm.enterprise.core.model_registry_v2 import EnterpriseModelRegistry, FallbackChain
from swarm.enterprise.core.safety_filter import InlineSafetyFilter, SafetyViolation
from swarm.enterprise.core.cache_manager import get_default_cache

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """مستند في قاعدة المعرفة."""
    doc_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    score: float = 0.0


@dataclass
class RetrievalResult:
    """نتيجة استرجاع RAG."""
    query: str
    documents: List[Document] = field(default_factory=list)
    reranked: bool = False
    total_score: float = 0.0
    model_used: str = ""
    latency_ms: float = 0.0


class KnowledgeAgentBase:
    """الفئة الأساسية لوكلاء المعرفة."""

    def __init__(
        self,
        role: str,
        chain: FallbackChain,
        executor: FallbackChainExecutor,
        safety: InlineSafetyFilter,
        cache=None,
    ):
        self.role = role
        self.chain = chain
        self.executor = executor
        self.safety = safety
        self.cache = cache or get_default_cache()

    def _hash_text(self, text: str) -> str:
        """تجزئة النص لاستخدامها كمفتاح تخزين مؤقت."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _execute_with_safety(self, prompt: str) -> Dict[str, Any]:
        """تنفيذ الاستعلام مع فحص السلامة والتخزين المؤقت."""
        # فحص المدخلات
        try:
            self.safety.check_input(prompt, agent_role=self.role)
        except SafetyViolation as e:
            logger.warning(f"{self.role} مدخل محظور: {e}")
            return {"error": "safety_violation", "stage": e.stage, "message": e.message}

        # تنفيذ عبر سلسلة الاحتياط
        result = self.executor.execute(self.role, prompt, chain=self.chain)

        # فحص المخرجات
        try:
            if result.success and result.output:
                self.safety.check_output(result.output, agent_role=self.role)
        except SafetyViolation as e:
            logger.warning(f"{self.role} مخرج محظور: {e}")
            return {"error": "safety_violation", "stage": e.stage, "message": e.message}

        return {
            "role": self.role,
            "model": result.chosen_model,
            "level": result.level_used,
            "output": result.output,
            "success": result.success,
            "latency_ms": result.total_latency_ms,
            "trace": result.trace,
        }


class KnowledgeDirector(KnowledgeAgentBase):
    """مدير المعرفة — ينسق بين الوكلاء الآخرين ويقرر الاستراتيجية."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("knowledge_director")
        super().__init__("knowledge_director", chain, executor, safety, cache)

    def plan_query(self, query: str) -> Dict[str, Any]:
        """يخطط لاستراتيجية الاستعلام بناءً على السؤال."""
        prompt = (
            f"كوحدة تنسيق معرفة، خطط لاستراتيجية البحث لهذا السؤال:\n"
            f"السؤال: {query}\n"
            f"حدد:\n"
            f"1. هل يحتاج RAG أم إجابة مباشرة\n"
            f"2. عدد المستندات المطلوبة\n"
            f"3. فلتر الجودة الأدنى\n"
            f"4. هل يحتاج إعادة ترتيب"
        )
        cache_key = f"plan:{self._hash_text(query)}"
        cached = self.cache.get(self.role, cache_key)
        if cached:
            return {"cached": True, "plan": cached}

        result = self._execute_with_safety(prompt)
        if result.get("success"):
            self.cache.set(self.role, cache_key, result.get("output"), ttl_sec=1800)
        return result


class KnowledgeCurator(KnowledgeAgentBase):
    """أمين المعرفة — يصنف ويقيّم جودة المعلومات."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("knowledge_curator")
        super().__init__("knowledge_curator", chain, executor, safety, cache)

    def evaluate_quality(self, content: str, source: str = "") -> Dict[str, Any]:
        """يقيّم جودة المحتوى."""
        prompt = (
            f"كوحدة تقييم جودة، قيّم هذا المحتوى:\n"
            f"المصدر: {source}\n"
            f"المحتوى: {content[:1000]}\n"
            f"أعطِ تقييماً من 0-10 مع التبرير."
        )
        return self._execute_with_safety(prompt)

    def classify(self, content: str) -> Dict[str, Any]:
        """يصنف المحتوى إلى فئة."""
        prompt = (
            f"صنّف هذا المحتوى في فئة واحدة من: تقني، طبي، قانوني، مالي، تعليمي، عام\n"
            f"المحتوى: {content[:500]}"
        )
        return self._execute_with_safety(prompt)


class KnowledgeRetriever(KnowledgeAgentBase):
    """مسترجع RAG — يبحث في قاعدة المتجهات (placeholder للآن)."""

    def __init__(self, executor, safety, cache=None, vector_store=None):
        chain = EnterpriseModelRegistry.get_chain("rag_retriever")
        super().__init__("rag_retriever", chain, executor, safety, cache)
        # متجر المتجهات — قابل للتوصيل (ChromaDB/Qdrant/pgvector)
        self.vector_store = vector_store or InMemoryVectorStore()

    def retrieve(self, query: str, top_k: int = 5, min_score: float = 0.0) -> RetrievalResult:
        """يسترجع المستندات الأكثر صلة."""
        cache_key = f"retrieve:{self._hash_text(query)}:{top_k}"
        cached = self.cache.get(self.role, cache_key)
        if cached:
            return cached

        # بحث في متجر المتجهات
        raw_docs = self.vector_store.search(query, top_k=top_k * 2)

        # تصفية حسب الحد الأدنى للجودة
        filtered = [d for d in raw_docs if d.score >= min_score][:top_k]
        result = RetrievalResult(
            query=query,
            documents=filtered,
            total_score=sum(d.score for d in filtered),
            model_used=self.chain.primary if self.chain else "placeholder",
            latency_ms=0.0,
        )

        self.cache.set(self.role, cache_key, result, ttl_sec=600)
        return result

    def generate_query_embedding(self, query: str) -> List[float]:
        """يولد embedding للاستعلام (placeholder)."""
        # في الإنتاج: استدعاء نموذج embeddings
        # الآن: hash-based placeholder
        h = self._hash_text(query)
        return [int(c, 16) / 15.0 for c in h]


class KnowledgeReranker(KnowledgeAgentBase):
    """معيد الترتيب — يحسن ترتيب النتائج باستخدام نموذج أقوى."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("rag_reranker")
        super().__init__("rag_reranker", chain, executor, safety, cache)

    def rerank(self, query: str, documents: List[Document], top_k: int = 5) -> RetrievalResult:
        """يعيد ترتيب المستندات حسب الصلة الحقيقية."""
        if not documents:
            return RetrievalResult(query=query, documents=[], reranked=True)

        cache_key = f"rerank:{self._hash_text(query)}:{len(documents)}"
        cached = self.cache.get(self.role, cache_key)
        if cached:
            return cached

        # بناء prompt مع المستندات
        docs_text = "\n".join(
            f"[{i}] (score={d.score:.2f}) {d.content[:200]}..."
            for i, d in enumerate(documents)
        )
        prompt = (
            f"أعد ترتيب هذه المستندات حسب صلتها بالسؤال:\n"
            f"السؤال: {query}\n\n"
            f"المستندات:\n{docs_text}\n\n"
            f"أعطِ الترتيب الجديد كقائمة أرقام مفصولة بفواصل."
        )

        result = self._execute_with_safety(prompt)

        if result.get("success"):
            # تحليل الترتيب الجديد من المخرج
            new_order = self._parse_order(str(result.get("output", "")), len(documents))
            reranked_docs = [documents[i] for i in new_order[:top_k]]
            retrieval = RetrievalResult(
                query=query,
                documents=reranked_docs,
                reranked=True,
                total_score=sum(d.score for d in reranked_docs),
                model_used=result.get("model", ""),
                latency_ms=result.get("latency_ms", 0.0),
            )
            self.cache.set(self.role, cache_key, retrieval, ttl_sec=600)
            return retrieval

        # fallback: الترتيب الأصلي
        return RetrievalResult(
            query=query,
            documents=documents[:top_k],
            reranked=False,
            total_score=sum(d.score for d in documents[:top_k]),
        )

    def _parse_order(self, text: str, max_n: int) -> List[int]:
        """يستخرج ترتيب الأرقام من نص المخرج."""
        numbers = re.findall(r'\b\d+\b', text)
        order = []
        for n in numbers:
            idx = int(n)
            if idx < max_n and idx not in order:
                order.append(idx)
        # إضافة المفقودين
        for i in range(max_n):
            if i not in order:
                order.append(i)
        return order


class KnowledgeDocParser(KnowledgeAgentBase):
    """محلل المستندات — يستخرج النصوص من PDFs/HTML/etc."""

    def __init__(self, executor, safety, cache=None):
        chain = EnterpriseModelRegistry.get_chain("doc_parser")
        super().__init__("doc_parser", chain, executor, safety, cache)

    def parse_text(self, raw_text: str, doc_type: str = "txt") -> Document:
        """يحلل نصاً خاماً وينظفه."""
        cleaned = self._clean_text(raw_text, doc_type)
        doc_id = self._hash_text(cleaned[:200])
        return Document(
            doc_id=doc_id,
            content=cleaned,
            metadata={"type": doc_type, "length": len(cleaned)},
            source="inline",
            score=1.0,
        )

    def parse_html(self, html: str) -> Document:
        """يستخرج النص من HTML (بسيط)."""
        # إزالة tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        # فك ترميز entities بسيطة
        text = text.replace('&nbsp;', ' ').replace('&', '&').replace('<', '<').replace('>', '>')
        return self.parse_text(text, "html")

    def summarize(self, content: str, max_words: int = 100) -> Dict[str, Any]:
        """يلخص المحتوى."""
        prompt = (
            f"لخص هذا المحتوى في {max_words} كلمة أو أقل:\n\n{content[:3000]}"
        )
        return self._execute_with_safety(prompt)

    def _clean_text(self, text: str, doc_type: str) -> str:
        """ينظف النص حسب النوع."""
        if doc_type == "html":
            text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text


class InMemoryVectorStore:
    """متجر متجهات بسيط في الذاكرة (placeholder لـ ChromaDB/Qdrant)."""

    def __init__(self):
        self.docs: List[Document] = []

    def add(self, doc: Document):
        self.docs.append(doc)

    def search(self, query: str, top_k: int = 10) -> List[Document]:
        """بحث بسيط بناءً على الكلمات المشتركة (case-insensitive + substring)."""
        query_lower = query.lower()
        query_words = set(re.findall(r'\w+', query_lower))
        scored = []
        for doc in self.docs:
            doc_lower = doc.content.lower()
            doc_words = set(re.findall(r'\w+', doc_lower))

            # 1. تطابق الكلمات الكاملة
            word_overlap = len(query_words & doc_words)

            # 2. تطابق جزئي (substring) — للكلمات المركبة مثل FastAPI
            substring_score = 0
            for qw in query_words:
                for dw in doc_words:
                    if len(qw) >= 3 and len(dw) >= 3:
                        if qw in dw or dw in qw:
                            substring_score += 0.5

            total = word_overlap + substring_score
            score = total / max(len(query_words), 1)

            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, doc in scored[:top_k]:
            doc.score = score
            results.append(doc)
        return results


class KnowledgeOrchestrator:
    """منسق قسم المعرفة — يدير تدفق RAG الكامل."""

    def __init__(self, executor, safety, cache=None):
        self.director = KnowledgeDirector(executor, safety, cache)
        self.curator = KnowledgeCurator(executor, safety, cache)
        self.retriever = KnowledgeRetriever(executor, safety, cache)
        self.reranker = KnowledgeReranker(executor, safety, cache)
        self.parser = KnowledgeDocParser(executor, safety, cache)
        self._vector_store = self.retriever.vector_store

    def add_document(self, content: str, source: str = "", doc_type: str = "txt") -> Document:
        """يضيف مستنداً لقاعدة المعرفة."""
        if doc_type == "html":
            doc = self.parser.parse_html(content)
        else:
            doc = self.parser.parse_text(content, doc_type)
        doc.source = source
        self._vector_store.add(doc)
        return doc

    def query(self, question: str, top_k: int = 5, rerank: bool = True) -> RetrievalResult:
        """استعلام RAG كامل: تخطيط → استرجاع → إعادة ترتيب."""
        # 1. تخطيط الاستراتيجية
        plan = self.director.plan_query(question)

        # 2. استرجاع أولي
        initial = self.retriever.retrieve(question, top_k=top_k * 2)

        # 3. إعادة ترتيب (اختياري)
        if rerank and initial.documents:
            final = self.reranker.rerank(question, initial.documents, top_k=top_k)
        else:
            final = RetrievalResult(
                query=question,
                documents=initial.documents[:top_k],
                reranked=False,
                total_score=initial.total_score,
            )

        return final

    def evaluate_and_curate(self, content: str, source: str = "") -> Dict[str, Any]:
        """يقيّم ويصنف المحتوى قبل الإضافة."""
        quality = self.curator.evaluate_quality(content, source)
        category = self.curator.classify(content)
        return {
            "quality": quality,
            "category": category,
            "approved": quality.get("success", False),
        }


# مصنع
def create_knowledge_dept(
    executor=None,
    safety=None,
    cache=None,
) -> KnowledgeOrchestrator:
    exe = executor or FallbackChainExecutor()
    sf = safety or InlineSafetyFilter()
    return KnowledgeOrchestrator(exe, sf, cache)


if __name__ == "__main__":
    # اختبار سريع
    dept = create_knowledge_dept()

    # إضافة مستندات
    doc1 = dept.add_document(
        "Python is a programming language created by Guido van Rossum in 1991.",
        source="wiki/python",
        doc_type="txt",
    )
    doc2 = dept.add_document(
        "FastAPI is a modern Python web framework built on Starlette and Pydantic.",
        source="docs/fastapi",
        doc_type="txt",
    )
    doc3 = dept.add_document(
        "<html><body><h1>RAG</h1><p>Retrieval-Augmented Generation combines search with LLMs.</p></body></html>",
        source="blog/rag",
        doc_type="html",
    )

    print(f"Added {len(dept._vector_store.docs)} documents")

    # استعلام
    print("\n=== Query: What is FastAPI? ===")
    result = dept.query("What is FastAPI?", top_k=2, rerank=True)
    for doc in result.documents:
        print(f"  - [{doc.score:.2f}] {doc.content[:100]}")

    print(f"\nReranked: {result.reranked}, Total score: {result.total_score:.2f}")

    # تقييم
    print("\n=== Curate new content ===")
    curation = dept.evaluate_and_curate(
        "Breaking news: AI model achieves new benchmark",
        source="news/ai",
    )
    print(f"Quality success: {curation['quality'].get('success')}")
    print(f"Category success: {curation['category'].get('success')}")