import json, urllib.request


class Ollama:
    def __init__(self, url):
        self.url = url.rstrip("/")

    def post(self, path, body, timeout=600):
        r = urllib.request.Request(self.url + path, data=json.dumps(body).encode(),
                                   headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(r, timeout=timeout)

    def chat(self, body):
        return json.load(self.post("/api/chat", body))

    def stream_chat(self, body):
        for line in self.post("/api/chat", body):
            yield json.loads(line)

    def caps(self, model):
        return json.load(self.post("/api/show", {"model": model})).get("capabilities", [])

    def digest(self, model):
        for m in json.load(urllib.request.urlopen(self.url + "/api/tags")).get("models", []):
            if m["name"] == model:
                return m.get("digest")
        return None

    def unload(self, model):
        try:
            self.post("/api/generate", {"model": model, "keep_alive": 0}).read()
        except Exception:
            pass
