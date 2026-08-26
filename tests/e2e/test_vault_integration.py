"""
E2E Test: Vault Integration
Tests that the vault server and client work together correctly.
"""
import pytest

# vault_client.py was intentionally removed in a88175e ("keep swarm core only").
# These e2e tests target that deleted module; skip cleanly instead of
# poisoning every collection run with an ImportError.
pytest.importorskip(
    "vault_client",
    reason="vault_client.py removed in a88175e; restore module to re-enable")

import time
import subprocess
import requests
import json
from vault_client import get_vault_client  # noqa: E402


class TestVaultIntegration:
    """End-to-end tests for vault integration."""
    
    @classmethod
    def setup_class(cls):
        """Start vault server before tests."""
        cls.server_process = subprocess.Popen(
            ["python3", "vault_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # Wait for server to start
        for _ in range(30):
            try:
                resp = requests.get("http://localhost:27123/health", timeout=1)
                if resp.status_code == 200:
                    break
            except:
                time.sleep(0.5)
        else:
            raise RuntimeError("Vault server failed to start")
        
        cls.client = get_vault_client()
    
    @classmethod
    def teardown_class(cls):
        """Stop vault server after tests."""
        if hasattr(cls, 'server_process'):
            cls.server_process.terminate()
            cls.server_process.wait(timeout=5)
    
    def test_health_check(self):
        """Test vault server health endpoint."""
        assert self.client.health_check() == True
    
    def test_write_and_read_note(self):
        """Test writing and reading a note."""
        content = "# Test Note\n\nThis is a test note for CI."
        result = self.client.write_note("test/e2e-test.md", content)
        # Server returns {'status': 'OK', 'path': '...'}
        assert result.get("status") == "OK"
        assert "path" in result
        
        read_content = self.client.read_note("test/e2e-test.md")
        assert "Test Note" in read_content
        assert "This is a test note for CI" in read_content
    
    def test_read_json_format(self):
        """Test reading note in JSON format."""
        note_str = self.client.read_note("test/e2e-test.md", format="json")
        # Server returns JSON string, not dict
        note = json.loads(note_str)
        assert isinstance(note, dict)
        assert "content" in note
        assert "frontmatter" in note
        assert "tags" in note
        assert "stat" in note
        assert "path" in note
    
    def test_append_note(self):
        """Test appending to a note."""
        self.client.write_note("test/append-test.md", "# Original\n\nFirst line.")
        self.client.append_note("test/append-test.md", "\n\nAppended line.")
        
        content = self.client.read_note("test/append-test.md")
        assert "Original" in content
        assert "First line" in content
        assert "Appended line" in content
    
    def test_search(self):
        """Test full-text search."""
        self.client.write_note("test/search-test.md", "# Search Test\n\nLooking for UNIQUE_TOKEN_12345")
        
        # Wait for indexing
        time.sleep(1)
        
        results = self.client.search("UNIQUE_TOKEN_12345")
        assert len(results) > 0
        assert any("UNIQUE_TOKEN_12345" in r.get("text", "") for r in results)
    
    def test_list_files(self):
        """Test listing files."""
        files = self.client.list_files("test/")
        assert isinstance(files, list)
        assert len(files) > 0
        # Should find our test files
        names = [f["path"] for f in files]
        assert "test/e2e-test.md" in names
    
    def test_tags(self):
        """Test tag listing."""
        self.client.write_note("test/tag-test.md", "# Tagged\n\n#swarm #test #ci")
        time.sleep(0.5)
        
        tags = self.client.list_tags()
        assert isinstance(tags, list)
        tag_names = [t["name"] for t in tags]
        assert "swarm" in tag_names
        assert "test" in tag_names
    
    def test_delete_note(self):
        """Test deleting a note."""
        self.client.write_note("test/delete-me.md", "# To Delete\n\nThis will be deleted.")
        result = self.client.delete_note("test/delete-me.md")
        assert result.get("status") == "deleted"
        
        # Verify it's gone
        files = self.client.list_files("test/")
        names = [f["path"] for f in files]
        assert "test/delete-me.md" not in names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
