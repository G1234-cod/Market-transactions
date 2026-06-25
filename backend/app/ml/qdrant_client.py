"""
Qdrant 向量数据库客户端（Docker HTTP 模式）
需要 Qdrant 服务运行: docker run -d -p 6333:6333 qdrant/qdrant

使用方式:
    from app.ml.qdrant_client import get_qdrant
    
    qdrant = get_qdrant()
    qdrant.add_item(item_id, vector, payload)
    results = qdrant.search(vector, top_k=5)
"""
import logging
from typing import Optional, List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.http import models
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


class QdrantSearch:
    """Qdrant 向量搜索引擎（HTTP 模式）"""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        collection_name: Optional[str] = None,
        vector_size: Optional[int] = None
    ):
        """
        初始化 Qdrant 客户端
        
        Args:
            host: Qdrant 服务地址，默认从 settings 读取
            port: Qdrant 服务端口，默认从 settings 读取
            collection_name: 集合名称，默认从 settings 读取
            vector_size: 向量维度，默认从 settings 读取
        """
        # 从配置读取参数
        self.host = host or settings.QDRANT_HOST
        self.port = port or settings.QDRANT_PORT
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.vector_size = vector_size or settings.QDRANT_VECTOR_SIZE
        
        # 连接 Qdrant
        self.client = QdrantClient(
            host=self.host,
            port=self.port,
            timeout=10,
        )
        
        # 确保集合存在
        self._ensure_collection()
        
        logger.info(f"✅ Qdrant 连接成功: {self.host}:{self.port}")
        logger.info(f"   集合: {self.collection_name}")
        logger.info(f"   向量维度: {self.vector_size}")
    
    def _ensure_collection(self):
        """确保集合存在"""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"✅ 创建集合: {self.collection_name}")
    
    def add_item(
        self,
        item_id: int,
        vector: np.ndarray,
        payload: Optional[Dict[str, Any]] = None
    ):
        """
        添加商品到索引
        
        Args:
            item_id: 商品ID
            vector: 特征向量 (512维)
            payload: 元数据 (title, category, price)
        """
        # 确保向量是 2D 格式
        if vector.ndim == 1:
            vector = vector.reshape(1, -1)
        
        # 检查向量维度
        if vector.shape[1] != self.vector_size:
            logger.warning(f"⚠️ 向量维度不匹配: {vector.shape[1]} != {self.vector_size}")
        
        point = models.PointStruct(
            id=item_id,
            vector=vector[0].tolist(),
            payload=payload or {}
        )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        logger.debug(f"✅ 商品 {item_id} 已加入索引")
    
    def add_items_batch(
        self,
        items: List[Dict[str, Any]]
    ):
        """
        批量添加商品到索引
        
        Args:
            items: 商品列表，每个包含 id, vector, payload
        """
        points = []
        for item in items:
            vector = item['vector']
            if vector.ndim == 1:
                vector = vector.reshape(1, -1)
            
            points.append(
                models.PointStruct(
                    id=item['id'],
                    vector=vector[0].tolist(),
                    payload=item.get('payload', {})
                )
            )
        
        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"✅ 批量索引完成: {len(points)} 个商品")
    
    def search(
        self,
        vector: np.ndarray,
        top_k: int = 10,
        filter_category: Optional[str] = None,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相似商品
        
        Args:
            vector: 查询向量
            top_k: 返回结果数量
            filter_category: 品类筛选
            score_threshold: 分数阈值（0-1）
        
        Returns:
            搜索结果列表，每个包含 id, score, payload
        """
        # 确保向量是 1D
        if vector.ndim == 2:
            vector = vector.flatten()
        
        # 构建过滤条件
        query_filter = None
        if filter_category:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="category",
                        match=models.MatchValue(value=filter_category)
                    )
                ]
            )
        
        # 使用 query_points API
        try:
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=vector.tolist(),
                limit=top_k,
                query_filter=query_filter,
                score_threshold=score_threshold,
            )
        except AttributeError:
            # 降级到 search API（旧版本兼容）
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector.tolist(),
                limit=top_k,
                query_filter=query_filter,
                score_threshold=score_threshold,
            )
        
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload or {}
            }
            for hit in results
        ]
    
    def search_by_id(
        self,
        item_id: int,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        根据商品ID查找相似商品
        
        Args:
            item_id: 商品ID
            top_k: 返回结果数量
        
        Returns:
            相似商品列表
        """
        # 先获取该商品的向量
        points = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[item_id],
            with_vectors=True,
        )
        
        if not points:
            logger.warning(f"⚠️ 商品 {item_id} 不在索引中")
            return []
        
        vector = points[0].vector
        
        # 搜索相似
        results = self.search(vector, top_k=top_k + 1)
        
        # 过滤掉自己
        return [r for r in results if r['id'] != item_id]
    
    def delete_item(self, item_id: int):
        """删除商品索引"""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=[item_id]
        )
        logger.info(f"🗑️ 商品 {item_id} 已从索引删除")
    
    def delete_by_filter(self, filter_condition: Dict[str, Any]):
        """
        根据条件删除索引
        
        Args:
            filter_condition: 过滤条件，如 {"category": "phone"}
        """
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key=k,
                    match=models.MatchValue(value=v)
                ) for k, v in filter_condition.items()
            ]
        )
        
        # 先获取符合条件的点
        points = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=query_filter,
            limit=1000,
            with_payload=False,
        )
        
        point_ids = [p.id for p in points[0]]
        if point_ids:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=point_ids
            )
            logger.info(f"🗑️ 已删除 {len(point_ids)} 个商品")
    
    def count(self) -> int:
        """获取索引中的向量数量"""
        return self.client.count(
            collection_name=self.collection_name
        ).count
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        获取集合信息
        
        Returns:
            Dict: 集合信息
        """
        try:
            info = self.client.get_collection(
                collection_name=self.collection_name
            )
            return {
                "name": self.collection_name,
                "vector_size": info.config.params.vectors.size,
                "distance": str(info.config.params.vectors.distance),
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "status": info.status,
            }
        except Exception as e:
            logger.error(f"❌ 获取集合信息失败: {e}")
            return {
                "name": self.collection_name,
                "error": str(e)
            }
    
    def clear(self):
        """清空集合"""
        self.client.delete_collection(self.collection_name)
        self._ensure_collection()
        logger.info("✅ 索引已清空")
    
    def health_check(self) -> bool:
        """检查 Qdrant 服务是否正常"""
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"❌ Qdrant 健康检查失败: {e}")
            return False


# ============================================================
# 单例实例
# ============================================================

_qdrant: Optional[QdrantSearch] = None


def get_qdrant() -> QdrantSearch:
    """获取 Qdrant 客户端单例"""
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantSearch()
    return _qdrant


def reset_qdrant():
    """重置 Qdrant 客户端（用于测试）"""
    global _qdrant
    _qdrant = None


# ============================================================
# 便捷函数
# ============================================================

def add_item_to_index(
    item_id: int,
    vector: np.ndarray,
    payload: Dict[str, Any]
):
    """快捷添加商品到索引"""
    qdrant = get_qdrant()
    qdrant.add_item(item_id, vector, payload)


def search_similar(
    vector: np.ndarray,
    top_k: int = 10,
    filter_category: Optional[str] = None
) -> List[Dict[str, Any]]:
    """快捷搜索相似商品"""
    qdrant = get_qdrant()
    return qdrant.search(vector, top_k, filter_category)


# ============================================================
# 调试函数（仅在显式调用时执行）
# ============================================================

def test_connection():
    """
    测试 Qdrant 连接（仅用于调试）
    
    使用方式:
        python -c "from app.ml.qdrant_client import test_connection; test_connection()"
    """
    print("=" * 50)
    print("🔍 测试 Qdrant 连接")
    print("=" * 50)
    
    try:
        qdrant = get_qdrant()
        count = qdrant.count()
        info = qdrant.get_collection_info()  # ✅ 现在可以正常调用
        
        print(f"✅ 连接成功！")
        print(f"   集合: {qdrant.collection_name}")
        print(f"   向量数量: {count}")
        print(f"   向量维度: {qdrant.vector_size}")
        print(f"   服务地址: {qdrant.host}:{qdrant.port}")
        print(f"   集合信息: {info}")
        return True
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False