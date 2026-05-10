"""向量索引模块 - 使用 sentence-transformers + Qdrant"""
from typing import List, Dict, Tuple, Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    import hashlib
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False

from storage.document import Document


class VectorIndexer:
    """向量索引构建器 - 支持 text2vec + Qdrant"""

    def __init__(
        self,
        embedding_model: str = "shibing624/text2vec-base-chinese",
        vector_dim: int = 384,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        collection_name: str = "search_docs",
    ):
        """
        Args:
            embedding_model: embedding 模型名称
            vector_dim: 向量维度
            qdrant_host: Qdrant 服务地址
            qdrant_port: Qdrant 端口
            collection_name: 集合名称
        """
        self.embedding_model = embedding_model
        self.vector_dim = vector_dim
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.collection_name = collection_name
        self.model = None
        self.qdrant_client = None
        self._use_qdrant = False

    def initialize(self) -> None:
        """初始化 embedding 模型和 Qdrant 连接"""
        if not HAS_SENTENCE_TRANSFORMERS:
            raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")

        # 加载 embedding 模型
        self.model = SentenceTransformer(self.embedding_model)

        # 尝试连接 Qdrant
        if HAS_QDRANT:
            try:
                self.qdrant_client = QdrantClient(
                    host=self.qdrant_host,
                    port=self.qdrant_port,
                    timeout=5,
                )
                self._setup_collection()
                self._use_qdrant = True
                print(f"VectorIndexer: Using Qdrant at {self.qdrant_host}:{self.qdrant_port}")
            except Exception as e:
                print(f"VectorIndexer: Qdrant connection failed, using in-memory. Error: {e}")
                self._use_qdrant = False
        else:
            print("VectorIndexer: Qdrant not installed, using in-memory storage")

        # 内存存储（备选）
        self.in_memory_vectors: Dict[str, np.ndarray] = {}
        self.in_memory_ids: List[str] = []

    def _setup_collection(self) -> None:
        """创建 Qdrant 集合"""
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_dim,
                        distance=Distance.COSINE,
                    ),
                )
                print(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            print(f"Failed to setup collection: {e}")
            self._use_qdrant = False

    def build_index(self, documents: List[Document]) -> None:
        """从文档列表构建向量索引"""
        if not self.model:
            self.initialize()

        texts = [doc.title + " " + doc.content for doc in documents]
        embeddings = self.model.encode(texts, show_progress_bar=True)

        doc_ids = [doc.url for doc in documents]

        if self._use_qdrant:
            self._index_to_qdrant(doc_ids, embeddings)
        else:
            self._index_in_memory(doc_ids, embeddings)

    def _index_to_qdrant(self, doc_ids: List[str], embeddings: np.ndarray) -> None:
        """索引到 Qdrant"""
        points = []
        for idx, (doc_id, embedding) in enumerate(zip(doc_ids, embeddings)):
            point_id = hashlib.md5(doc_id.encode()).digest()[:16].hex()
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding.tolist(),
                    payload={"url": doc_id},
                )
            )
            if len(points) >= 100:
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                )
                points = []

        if points:
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points,
            )

    def _index_in_memory(self, doc_ids: List[str], embeddings: np.ndarray) -> None:
        """索引到内存"""
        self.in_memory_ids = doc_ids
        self.in_memory_vectors = {
            doc_id: emb for doc_id, emb in zip(doc_ids, embeddings)
        }

    def search(self, query: str, top_k: int = 20) -> List[Tuple[str, float]]:
        """
        向量搜索

        Args:
            query: 查询词
            top_k: 返回前 k 个结果

        Returns:
            List[(url, score)]: 按分数降序排列
        """
        if not self.model:
            self.initialize()

        # 编码查询
        query_embedding = self.model.encode([query])[0]

        if self._use_qdrant:
            return self._search_qdrant(query_embedding, top_k)
        else:
            return self._search_in_memory(query_embedding, top_k)

    def _search_qdrant(self, query_embedding: np.ndarray, top_k: int) -> List[Tuple[str, float]]:
        """Qdrant 搜索"""
        try:
            results = self.qdrant_client.search(
                collection_name=self.collection_name,
                vector=query_embedding.tolist(),
                limit=top_k,
            )
            return [(r.payload["url"], r.score) for r in results]
        except Exception as e:
            print(f"Qdrant search failed: {e}")
            return self._search_in_memory(query_embedding, top_k)

    def _search_in_memory(self, query_embedding: np.ndarray, top_k: int) -> List[Tuple[str, float]]:
        """内存搜索（余弦相似度）"""
        if not self.in_memory_vectors:
            return []

        scores: Dict[str, float] = {}
        for doc_id, doc_emb in self.in_memory_vectors.items():
            # 余弦相似度
            cos_sim = np.dot(query_embedding, doc_emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_emb) + 1e-8
            )
            scores[doc_id] = float(cos_sim)

        # 排序返回
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:top_k]

    def get_scores(self, query: str) -> Dict[str, float]:
        """获取查询对所有文档的向量相似度分数"""
        if not self.model:
            self.initialize()

        query_embedding = self.model.encode([query])[0]
        scores: Dict[str, float] = {}

        if self._use_qdrant:
            # Qdrant 不容易获取所有分数，改用内存
            pass

        for doc_id, doc_emb in self.in_memory_vectors.items():
            cos_sim = np.dot(query_embedding, doc_emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_emb) + 1e-8
            )
            scores[doc_id] = float(cos_sim)

        return scores

    @staticmethod
    def normalize_scores(scores: Dict[str, float]) -> Dict[str, float]:
        """将分数归一化到 [0, 1]"""
        if not scores:
            return {}
        max_score = max(scores.values())
        min_score = min(scores.values())
        if max_score == min_score:
            return {k: 1.0 for k in scores}
        return {k: (v - min_score) / (max_score - min_score) for k, v in scores.items()}