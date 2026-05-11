import urllib.request
import urllib.error
import json
import socket
from dragoman import secrets

def discover_openai_compat(host: str, api_key: str = None) -> list[str]:
    """Discover models from OpenAI-compatible endpoint."""
    try:
        url = f"{host.rstrip('/')}/models"
        if "api.openai.com" in host and "/v1" not in url:
            url = f"https://api.openai.com/v1/models"
        req = urllib.request.Request(url)
        if api_key:
            resolved = secrets.resolve(api_key)
            if resolved:
                req.add_header("Authorization", f"Bearer {resolved}")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return [m["id"] for m in data.get("data", [])]
    except Exception as e:
        # print(f"OpenAI compat discovery failed: {e}")
        return []

def discover_gemini(api_key: str = None) -> list[str]:
    """Discover models from Google Generative Language API."""
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        if api_key:
            resolved = secrets.resolve(api_key)
            if resolved:
                url += f"?key={resolved}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return [m["name"] for m in data.get("models", [])]
    except Exception as e:
        # print(f"Gemini discovery failed: {e}")
        return []

def discover_anthropic(api_key: str = None) -> list[str]:
    """Discover models from Anthropic."""
    try:
        url = "https://api.anthropic.com/v1/models"
        req = urllib.request.Request(url)
        req.add_header("anthropic-version", "2023-06-01")
        if api_key:
            resolved = secrets.resolve(api_key)
            if resolved:
                req.add_header("x-api-key", resolved)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return [m["id"] for m in data.get("data", [])]
    except Exception as e:
        return []

def parse_catalogue() -> list[dict]:
    """Parse the model-catalogue.md into a structured list of dictionaries."""
    import pathlib
    cat_path = pathlib.Path(__file__).parent / "templates" / "model-catalogue.md"
    if not cat_path.exists():
        return []
    
    rows = []
    lines = cat_path.read_text().splitlines()
    in_table = False
    for line in lines:
        if line.strip().startswith('|'):
            if '---' in line:
                in_table = True
                continue
            if in_table:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 12:
                    rows.append({
                        "model_id": parts[1],
                        "provider": parts[2],
                        "speed": parts[3],
                        "quality": parts[6],
                        "strengths": parts[7],
                        "weaknesses": parts[8],
                        "context": parts[9],
                        "suitable_for": parts[10],
                        "propose": parts[11].lower() == "yes",
                    })
    return rows

def map_discovered_models(provider: str, discovered: list[str]) -> tuple[list[dict], list[dict], list[str]]:
    """Compare discovered raw models to catalogue families. Returns (approved_families, rejected_families, unknown_families)."""
    catalogue = parse_catalogue()
    approved_map = {}
    rejected_map = {}
    unknown = set()
    
    for raw_id in discovered:
        # Strip common prefixes
        clean_id = raw_id.replace("models/", "")
        
        # Find the longest matching family prefix in the catalogue
        match = None
        longest_len = 0
        for c in catalogue:
            # Match family prefixes
            if clean_id.startswith(c["model_id"]) and len(c["model_id"]) > longest_len:
                match = c
                longest_len = len(c["model_id"])
                
        if match:
            # We matched a family! Store the family metadata once.
            family_id = match["model_id"]
            if match["propose"]:
                approved_map[family_id] = match
            else:
                rejected_map[family_id] = match
        else:
            # Fallback heuristic for totally unknown families
            import re
            base = re.sub(r'-\d{2}-\d{4}$', '', clean_id)
            base = re.sub(r'-\d{8}$', '', base)
            base = re.sub(r'-preview.*$', '', base)
            base = re.sub(r'-latest.*$', '', base)
            base = base.strip("-")
            unknown.add(base)
            
    approved = list(approved_map.values())
    rejected = list(rejected_map.values())
    
    known_ids = set(approved_map.keys()) | set(rejected_map.keys())
    unknown_list = [u for u in unknown if u not in known_ids]
    
    return approved, rejected, sorted(unknown_list)
