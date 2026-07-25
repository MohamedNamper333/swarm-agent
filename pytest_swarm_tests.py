#!/usr/bin/env python3
"""
Pytest suite for Swarm Agent System tests.
Run with: pytest pytest_swarm_tests.py -v
"""

import pytest
import requests
import json
import time

# Configuration
MEILI_URL = "http://localhost:7700"
MEILI_KEY = "test-master-key"
HEADERS = {"Authorization": f"Bearer {MEILI_KEY}", "Content-Type": "application/json"}
VAULT_URL = "http://127.0.0.1:27123"
VAULT_KEY = "swarm-evolution-2025"


class TestMeilisearch:
    """Tests for Meilisearch integration"""
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_index(self):
        """Create test index with sample documents"""
        # Create index
        resp = requests.post(
            f"{MEILI_URL}/indexes",
            headers=HEADERS,
            json={"uid": "mukh-unified", "primaryKey": "id"}
        )
        assert resp.status_code in [200, 201], f"Failed to create index: {resp.text}"
        
        # Add test documents
        docs = [
            {"id": "1", "title": "نظام الوكلاء الذكيين", "content": "نظام الوكلاء الذكيين (AI Agents) هو نظام يستخدم نماذج لغوية كبيرة لأداء مهام معقدة.", "filename": "ai-agents-ar.md", "language": "ar"},
            {"id": "2", "title": "الذكاء الاصطناعي التأسيسي", "content": "Constitutional AI هو منهج لتدريب النماذج بحيث تتبع مبادئ دستورية محددة.", "filename": "constitutional-ai-ar.md", "language": "ar"},
            {"id": "3", "title": "Swarm Architecture", "content": "The swarm architecture uses multiple specialized agents working in parallel to solve complex problems.", "filename": "swarm-arch-en.md", "language": "en"},
            {"id": "4", "title": "Agent Orchestration Patterns", "content": "Multi-agent orchestration patterns include supervisor, hierarchical, and swarm topologies for task distribution.", "filename": "orchestration-en.md", "language": "en"},
            {"id": "5", "title": "Meilisearch Arabic Search", "content": "Meilisearch supports Arabic language search with built-in analyzer for tokenization and stemming.", "filename": "meilisearch-ar.md", "language": "en"},
        ]
        
        resp = requests.post(f"{MEILI_URL}/indexes/mukh-unified/documents", headers=HEADERS, json=docs)
        assert resp.status_code in [200, 202], f"Failed to add documents: {resp.text}"
        
        # Wait for indexing
        task_uid = resp.json().get('taskUid')
        if task_uid:
            for _ in range(30):
                task_resp = requests.get(f"{MEILI_URL}/tasks/{task_uid}", headers=HEADERS)
                if task_resp.json().get('status') == 'succeeded':
                    break
                time.sleep(0.5)
        
        yield
        
        # Cleanup
        requests.delete(f"{MEILI_URL}/indexes/mukh-unified", headers=HEADERS)
    
    def test_health_check(self):
        """Test Meilisearch health endpoint"""
        resp = requests.get(f"{MEILI_URL}/health")
        assert resp.status_code == 200
        assert resp.json().get('status') == 'available'
    
    def test_index_exists(self):
        """Test index exists"""
        resp = requests.get(f"{MEILI_URL}/indexes/mukh-unified", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data['uid'] == 'mukh-unified'
        assert data['primaryKey'] == 'id'
    
    def test_document_count(self):
        """Test index has documents"""
        resp = requests.get(f"{MEILI_URL}/indexes/mukh-unified/stats", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data['numberOfDocuments'] >= 5
    
    def test_arabic_search(self):
        """Test Arabic search works"""
        queries = [
            ("الذكاء الاصطناعي", 1),  # At least 1 result
            ("نظام", 1),
            ("وكلاء", 1),
        ]
        
        for query, min_results in queries:
            resp = requests.post(
                f"{MEILI_URL}/indexes/mukh-unified/search",
                headers=HEADERS,
                json={"q": query, "limit": 10}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data['estimatedTotalHits'] >= min_results, f"Query '{query}' returned {data['estimatedTotalHits']} results, expected >= {min_results}"
    
    def test_english_search(self):
        """Test English search works"""
        queries = [
            ("swarm", 1),
            ("agent", 1),
            ("architecture", 1),
        ]
        
        for query, min_results in queries:
            resp = requests.post(
                f"{MEILI_URL}/indexes/mukh-unified/search",
                headers=HEADERS,
                json={"q": query, "limit": 10}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data['estimatedTotalHits'] >= min_results, f"Query '{query}' returned {data['estimatedTotalHits']} results"


class TestVaultServer:
    """Tests for Vault REST Server (if running)"""
    
    def test_vault_server_if_running(self):
        """Test vault server if it's running"""
        try:
            resp = requests.get(
                f"{VAULT_URL}/vault/read",
                params={"path": "AL-MUKH/config.yaml"},
                headers={"Authorization": f"Bearer {VAULT_KEY}"},
                timeout=3
            )
            # Server is running - accept 200 or 404
            assert resp.status_code in [200, 404], f"Vault server error: {resp.status_code}"
        except requests.exceptions.ConnectionError:
            pytest.skip("Vault server not running")


class TestSwarmSimulation:
    """Simulate swarm worker operations"""
    
    def test_worker_research_simulation(self):
        """Simulate a worker doing research via Meilisearch"""
        # Worker needs info on "Constitutional AI"
        resp = requests.post(
            f"{MEILI_URL}/indexes/mukh-unified/search",
            headers=HEADERS,
            json={"q": "Constitutional AI", "limit": 5}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['estimatedTotalHits'] >= 1
        
        # Simulate worker synthesis
        hits = data['hits']
        assert len(hits) > 0
        
        # Extract context
        context = "\n".join([h.get('content', '')[:200] for h in hits])
        assert len(context) > 50
        
        # Simulate synthesis output
        synthesis = f"Based on {len(hits)} documents about Constitutional AI:\n\nKey findings:\n{context[:500]}"
        assert "Constitutional AI" in synthesis
        assert len(synthesis) > 100
    
    def test_parallel_worker_simulation(self):
        """Simulate multiple workers searching in parallel"""
        import concurrent.futures
        
        queries = ["swarm", "agent", "orchestration", "constitutional", "arabic"]
        
        def search(q):
            resp = requests.post(
                f"{MEILI_URL}/indexes/mukh-unified/search",
                headers=HEADERS,
                json={"q": q, "limit": 5}
            )
            return resp.json()
        
        # Parallel execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(search, q): q for q in queries}
            results = {}
            for future in concurrent.futures.as_completed(futures):
                q = futures[future]
                results[q] = future.result()
        
        # All should succeed
        for q, result in results.items():
            assert 'hits' in result
            assert result['estimatedTotalHits'] >= 0


class TestDocumentationAccuracy:
    """Test that documentation claims match reality"""
    
    def test_worker_count_consistency(self):
        """Verify worker agents in opencode.json"""
        import json
        with open('/home/kali/swarm-agent/opencode.json') as f:
            data = json.load(f)
        
        agents = data.get('agent', {})
        # Core workers (excluding swarm coordinator and vision variants)
        core_workers = [
            'swarm-worker-qa', 'innovator', 'critic', 'architect', 
            'explorer', 'reviewer', 'reasoner', 'vision-coder',
            'laguna-s-2-1', 'ling-3-0-flash'
        ]
        
        found = [k for k in agents.keys() if k in core_workers]
        assert len(found) == 10, f"Expected 10 core workers, found {len(found)}: {found}"
        
        # Total agents including special ones
        total_agents = len(agents)
        assert total_agents == 13, f"Expected 13 total agents, found {total_agents}"
    
    def test_model_uniqueness(self):
        """Document actual unique model count"""
        import json
        with open('/home/kali/swarm-agent/opencode.json') as f:
            data = json.load(f)
        
        models = set()
        for agent_name, agent_config in data.get('agent', {}).items():
            if 'model' in agent_config:
                models.add(agent_config['model'])
        
        # Should be 9 unique models (not 10, not 13)
        assert len(models) == 9, f"Expected 9 unique models, found {len(models)}: {models}"
    
    def test_no_approved_status_in_evolution_plan(self):
        """Evolution plan should be 'planned' not 'approved'"""
        with open('/home/kali/swarm-agent/SWARM-EVOLUTION-PLAN.md') as f:
            content = f.read()
        
        assert 'status: "planned"' in content or "status: 'planned'" in content
        assert 'status: "approved"' not in content


# Run with: pytest pytest_swarm_tests.py -v --tb=short
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])