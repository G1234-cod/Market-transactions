"""
Qdrant 向量数据库客户端
"""
from qdrant_client import QdrantClient
from qdrant_client.http import models
import numpy as np
import logging

logger = logging.getLogger(__name__)


class QdrantSearch:
    
    COLLECTION_NAME = "market_items"
    VECTOR_SIZE = 512
    
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        self._ensure_collection()
        logger.info(f"✅ Qdrant 连接成功: {host}:{port}")
    
    def _ensure_collection(self):
        collections = self.client.get_collections().collections
        exists = any(c.name == self.COLLECTION_NAME for c in collections)
        if not exists:
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=self.VECTOR_SIZE,
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"✅ 创建 collection: {self.COLLECTION_NAME}")
    
    def add_item(self, item_id: int, vector: np.ndarray, payload: dict = None):
        if vector.ndim == 1:
            vector = vector.reshape(1, -1)
        point = models.PointStruct(
            id=item_id,
            vector=vector[0].tolist(),
            payload=payload or {}
        )
        self.client.upsert(collection_name=self.COLLECTION_NAME, points=[point])
        logger.debug(f"✅ 商品 {item_id} 已加入索引")
    
    def search(self, vector: np.ndarray, top_k: int = 10, filter_condition: dict = None) -> list:
        """搜索相似向量（修复版）"""
        if vector.ndim == 1:
            vector = vector.reshape(1, -1)
        
        query_filter = None
        if filter_condition:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key=k,
                        match=models.MatchValue(value=v)
                    ) for k, v in filter_condition.items()
                ]
            )
        
        # ✅ 使用 query_points 替代 search
        results = self.client.query_points(
            collection_name=self.COLLECTION_NAME,
            query=vector[0].tolist(),
            limit=top_k,
            query_filter=query_filter
        )
        
        return [
            (hit.id, hit.score, hit.payload)
            for hit in results.points
        ]
    
    def count(self) -> int:
        return self.client.count(collection_name=self.COLLECTION_NAME).count
    
    def clear(self):
        self.client.delete_collection(self.COLLECTION_NAME)
        self._ensure_collection()
        logger.info("✅ 索引已清空")


_qdrant = None

def get_qdrant():
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantSearch()
    return _qdrant