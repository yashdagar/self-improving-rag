import hashlib
import math
import re


class HashEmbedder:
    model_name = "test-hash-embedder"
    loaded = True
    dimensions = 64

    def embed(self, texts):
        return [self._vector(text) for text in texts]

    def _vector(self, text):
        vector = [0.0] * self.dimensions
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            index = int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]
