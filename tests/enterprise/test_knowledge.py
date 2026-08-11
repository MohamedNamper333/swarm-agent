"""
اختبارات قسم المعرفة (Knowledge)
"""
import sys
sys.path.insert(0, '/home/kali/swarm-agent')

from swarm.enterprise.knowledge import (
    create_knowledge_dept,
    KnowledgeOrchestrator,
    InMemoryVectorStore,
    Document,
    RetrievalResult,
)


def test_knowledge_factory():
    """اختبار: factory function"""
    dept = create_knowledge_dept()
    assert isinstance(dept, KnowledgeOrchestrator)
    print("✓ test_knowledge_factory")


def test_add_text_document():
    """اختبار: إضافة مستند نصي"""
    dept = create_knowledge_dept()
    doc = dept.add_document("Python is a programming language.", source="wiki")
    assert isinstance(doc, Document)
    assert doc.content == "Python is a programming language."
    assert doc.source == "wiki"
    assert len(dept._vector_store.docs) == 1
    print("✓ test_add_text_document")


def test_add_html_document():
    """اختبار: إضافة مستند HTML"""
    dept = create_knowledge_dept()
    html = "<html><body><h1>Title</h1><script>alert('x')</script><p>Content here</p></body></html>"
    doc = dept.add_document(html, source="web", doc_type="html")
    # يجب إزالة script tag
    assert "alert" not in doc.content.lower() or "script" not in doc.content.lower()
    assert "Content here" in doc.content
    print("✓ test_add_html_document")


def test_vector_store_search():
    """اختبار: بحث في متجر المتجهات"""
    store = InMemoryVectorStore()
    store.add(Document(doc_id="1", content="Python is a programming language"))
    store.add(Document(doc_id="2", content="FastAPI is a web framework"))
    store.add(Document(doc_id="3", content="RAG combines retrieval with LLMs"))

    results = store.search("FastAPI", top_k=2)
    assert len(results) > 0
    assert "FastAPI" in results[0].content or "fastapi" in results[0].content.lower()
    print("✓ test_vector_store_search")


def test_vector_store_substring_match():
    """اختبار: مطابقة جزئية (substring)"""
    store = InMemoryVectorStore()
    store.add(Document(doc_id="1", content="FastAPI framework"))
    results = store.search("FastAPI framework", top_k=1)
    assert len(results) > 0
    assert results[0].score > 0
    print("✓ test_vector_store_substring_match")


def test_rag_query():
    """اختبار: استعلام RAG كامل"""
    dept = create_knowledge_dept()
    dept.add_document("Python was created by Guido van Rossum.", source="wiki")
    dept.add_document("FastAPI is a modern Python web framework.", source="docs")

    result = dept.query("FastAPI Python framework", top_k=2, rerank=False)
    assert isinstance(result, RetrievalResult)
    assert len(result.documents) >= 1
    assert result.documents[0].score > 0
    print("✓ test_rag_query")


def test_rag_query_with_rerank():
    """اختبار: استعلام مع إعادة ترتيب"""
    dept = create_knowledge_dept()
    dept.add_document("Document A: about cats", source="a")
    dept.add_document("Document B: about dogs", source="b")
    dept.add_document("Document C: about cats and dogs", source="c")

    result = dept.query("cats", top_k=2, rerank=True)
    assert isinstance(result, RetrievalResult)
    assert result.reranked == True
    assert len(result.documents) >= 1
    print("✓ test_rag_query_with_rerank")


def test_curator_evaluate():
    """اختبار: تقييم الجودة"""
    dept = create_knowledge_dept()
    result = dept.evaluate_and_curate("High quality technical content", source="tech")
    assert "quality" in result
    assert "category" in result
    print("✓ test_curator_evaluate")


def test_doc_parser_html():
    """اختبار: HTML parser"""
    dept = create_knowledge_dept()
    html = "<html><head><title>Test</title></head><body><p>Hello world</p></body></html>"
    doc = dept.parser.parse_html(html)
    assert isinstance(doc, Document)
    assert "Hello world" in doc.content
    # tags should be removed
    assert "<p>" not in doc.content
    print("✓ test_doc_parser_html")


def test_doc_parser_summarize():
    """اختبار: تلخيص المستند"""
    dept = create_knowledge_dept()
    long_text = "Lorem ipsum dolor sit amet. " * 50
    result = dept.parser.summarize(long_text, max_words=10)
    assert "role" in result
    assert result["role"] == "doc_parser"
    print("✓ test_doc_parser_summarize")


def test_director_plan_query():
    """اختبار: تخطيط الاستراتيجية"""
    dept = create_knowledge_dept()
    result = dept.director.plan_query("What is machine learning?")
    assert "role" in result
    assert result["role"] == "knowledge_director"
    print("✓ test_director_plan_query")


def test_no_results_empty_query():
    """اختبار: استعلام بدون نتائج"""
    dept = create_knowledge_dept()
    dept.add_document("Python programming", source="x")
    result = dept.query("Quantum physics", top_k=3, rerank=False)
    # قد لا يجد نتائج لكن يجب ألا يفشل
    assert isinstance(result, RetrievalResult)
    print("✓ test_no_results_empty_query")


if __name__ == "__main__":
    test_knowledge_factory()
    test_add_text_document()
    test_add_html_document()
    test_vector_store_search()
    test_vector_store_substring_match()
    test_rag_query()
    test_rag_query_with_rerank()
    test_curator_evaluate()
    test_doc_parser_html()
    test_doc_parser_summarize()
    test_director_plan_query()
    test_no_results_empty_query()
    print("\n✅ جميع اختبارات Knowledge نجحت (12/12)")