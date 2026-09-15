import pytest

from app.adapters.driven.storage.chroma_adapter import _EmbeddingPortFunction


class FakeEmbeddingPort:
    def __init__(self, vectors: dict[str, list[float]] | None = None) -> None:
        self._vectors = vectors or {}

    def embed_batch(self, texts: list[str], show_progress_bar: bool = False):
        return [self._vectors.get(text) for text in texts]


def test_embedding_port_function_returns_vectors_in_order():
    fn = _EmbeddingPortFunction(FakeEmbeddingPort({"a": [1.0, 2.0], "b": [3.0, 4.0]}))
    result = fn(["a", "b"])
    # EmbeddingFunction.__init_subclass__ (chromadb) normaliza o retorno de
    # __call__ pra ndarray - comparar via tolist() em vez de == direto.
    assert [list(vec) for vec in result] == [[1.0, 2.0], [3.0, 4.0]]


def test_embedding_port_function_raises_when_embedding_fails():
    fn = _EmbeddingPortFunction(FakeEmbeddingPort({"a": [1.0]}))
    with pytest.raises(RuntimeError):
        fn(["a", "missing"])


def test_embedding_port_function_name():
    assert _EmbeddingPortFunction.name() == "embedding-port"
