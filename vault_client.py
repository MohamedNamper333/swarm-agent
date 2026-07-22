"""
Vault REST API Client - Direct HTTP access to Obsidian vault
Replaces broken obsidian-mcp-server tools
"""
import requests
import json
from typing import Dict, List, Optional, Any
from pathlib import Path


class VaultClient:
    """Direct REST API client for Obsidian vault server"""
    
    def __init__(self, base_url: str = "http://localhost:27123", api_key: str = "swarm-evolution-2025"):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    # ============ Vault Operations ============
    
    def list_files(self, path: str = "") -> List[Dict]:
        """List files/folders in vault path"""
        url = f"{self.base_url}/vault/{path}" if path else f"{self.base_url}/vault/"
        resp = self.session.get(url)
        resp.raise_for_status()
        data = resp.json()
        return data.get("files", data) if isinstance(data, dict) else data
    
    def read_note(self, path: str, format: str = "text") -> str:
        """Read note content"""
        url = f"{self.base_url}/vault/{path}"
        headers = self.headers.copy()
        if format == "json":
            headers["Accept"] = "application/vnd.olrapi.note+json"
        resp = self.session.get(url, headers=headers)
        resp.raise_for_status()
        return resp.text
    
    def write_note(self, path: str, content: str) -> Dict:
        """Create or overwrite note (uses PUT)"""
        url = f"{self.base_url}/vault/{path}"
        resp = self.session.put(url, data=content, headers={"Content-Type": "text/markdown"})
        resp.raise_for_status()
        return resp.json()
    
    def append_note(self, path: str, content: str) -> Dict:
        """Append to existing note (uses POST)"""
        url = f"{self.base_url}/vault/{path}"
        resp = self.session.post(url, data=content, headers={"Content-Type": "text/markdown"})
        resp.raise_for_status()
        return resp.json()
    
    def patch_note(self, path: str, operations: List[Dict]) -> Dict:
        """Patch note with JSON operations"""
        url = f"{self.base_url}/vault/{path}"
        resp = self.session.patch(url, json={"operations": operations})
        resp.raise_for_status()
        return resp.json()
    
    def delete_note(self, path: str) -> Dict:
        """Delete note"""
        url = f"{self.base_url}/vault/{path}"
        resp = self.session.delete(url)
        resp.raise_for_status()
        return resp.json()
    
    # ============ Search Operations ============
    
    def search(self, query: str, context_length: int = 100, flat: bool = True) -> List[Dict]:
        """Full-text search - returns standardized list
        
        Args:
            query: Search query
            context_length: Context chars around matches
            flat: If True, flatten hits/matches/match into simple list
        """
        url = f"{self.base_url}/search/"
        resp = self.session.get(url, params={"query": query, "contextLength": context_length})
        resp.raise_for_status()
        data = resp.json()
        
        if flat and isinstance(data, dict) and "hits" in data:
            # Flatten MCP format: hits -> matches -> match
            results = []
            for hit in data["hits"]:
                for match_wrapper in hit.get("matches", []):
                    match = match_wrapper.get("match", {})
                    if match:
                        results.append(match)
            return results
        
        # Handle both formats: direct list or {"hits": [...]}
        if isinstance(data, dict) and "hits" in data:
            return data["hits"]
        return data
    
    def search_simple(self, query: str, context_length: int = 100, flat: bool = True) -> List[Dict]:
        """Simple search - returns standardized list"""
        url = f"{self.base_url}/search/simple"
        resp = self.session.get(url, params={"query": query, "contextLength": context_length})
        resp.raise_for_status()
        data = resp.json()
        
        if flat and isinstance(data, dict) and "hits" in data:
            results = []
            for hit in data["hits"]:
                for match_wrapper in hit.get("matches", []):
                    match = match_wrapper.get("match", {})
                    if match:
                        results.append(match)
            return results
        
        if isinstance(data, dict) and "hits" in data:
            return data["hits"]
        return data
    
    # ============ Metadata ============
    
    def list_tags(self) -> List[Dict]:
        """List all tags with counts"""
        url = f"{self.base_url}/tags/"
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json().get("tags", [])
    
    def list_commands(self) -> List[Dict]:
        """List available Obsidian commands"""
        url = f"{self.base_url}/commands/"
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json().get("commands", [])
    
    def execute_command(self, command_id: str) -> Dict:
        """Execute Obsidian command"""
        url = f"{self.base_url}/commands/{command_id}"
        resp = self.session.post(url)
        resp.raise_for_status()
        return resp.json()
    
    # ============ Utilities ============
    
    def health_check(self) -> bool:
        """Check if vault server is running"""
        try:
            resp = self.session.get(f"{self.base_url}/vault/", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False


# Convenience functions for direct use
def get_vault_client() -> VaultClient:
    """Get configured vault client"""
    return VaultClient()


# Example usage
if __name__ == "__main__":
    client = get_vault_client()
    
    if client.health_check():
        print("✅ Vault server connected")
        
        # List files
        files = client.list_files()
        print(f"\n📁 Files ({len(files)}):")
        for f in files:
            print(f"  {f['path']} ({f['type']})")
        
        # Search
        results = client.search("swarm")
        print(f"\n🔍 Search 'swarm' ({len(results)} results):")
        for r in results[:3]:
            print(f"  {r['path']} - score: {r.get('score', 'N/A')}")
        
        # Tags
        tags = client.list_tags()
        print(f"\n🏷️ Tags ({len(tags)}):")
        for t in tags[:5]:
            print(f"  #{t['name']} ({t['count']})")
    else:
        print("❌ Vault server not running")
