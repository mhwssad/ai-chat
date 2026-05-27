"""数据仓库基类。

提供通用的 CRUD 操作封装，各业务仓库继承此类即可获得标准数据库操作。

使用方式::

    from src.ai.storage.database import get_session
    from src.ai.storage.base_repository import BaseRepository
    from src.ai.storage.runtime_models import Session

    class SessionRepository(BaseRepository[Session]):
        model = Session

    with get_session() as session:
        repo = SessionRepository(session)
        obj = repo.create(session_id="xxx", title="新会话")
        obj = repo.get_by_id("session_id")
        repo.update(obj, title="更新后的标题")
        repo.delete(obj)
        sessions = repo.list(limit=10, offset=0)
"""


from datetime import datetime
from typing import Any, Generic, NamedTuple, TypeVar

from sqlalchemy import func, inspect
from sqlmodel import SQLModel, Session as SqlSession, select

T = TypeVar("T", bound=SQLModel)


class Page(NamedTuple):
    """分页查询结果。"""

    items: list[Any]
    total: int
    limit: int
    offset: int


class BaseRepository(Generic[T]):
    """数据仓库基类，提供通用 CRUD 操作。

    Type Parameters:
        T: 模型类型，必须继承自 SQLModel

    Attributes:
        model: 仓库操作的模型类（子类必须定义）
        session: SQLAlchemy 会话实例
    """

    model: type[T]

    def __init__(self, session: SqlSession) -> None:
        self.session = session

    # ==================== 内部工具方法 ====================

    def _pk_columns(self) -> list[Any]:
        """通过 SQLAlchemy inspect 获取主键列，避免 dir() 遍历。"""
        return list(inspect(self.model).primary_key)

    def _column_names(self) -> set[str]:
        """获取模型所有列名集合，用于字段合法性校验。"""
        return {col.name for col in inspect(self.model).columns}

    def _apply_filters(self, stmt: Any, **filters: Any) -> Any:
        """向查询语句追加等值过滤条件，自动忽略无效字段名。"""
        valid = self._column_names()
        for name, value in filters.items():
            if name in valid:
                stmt = stmt.where(getattr(self.model, name) == value)
        return stmt

    # ==================== 查询 ====================

    def get_by_id(self, pk_value: Any) -> T | None:
        """根据主键获取单条记录。"""
        pk_cols = self._pk_columns()
        if len(pk_cols) != 1:
            raise ValueError(
                f"{self.model.__name__} 有复合主键，请使用 get_by_field 或自定义查询"
            )
        stmt = select(self.model).where(pk_cols[0] == pk_value)
        return self.session.exec(stmt).first()

    def get_by_field(self, field_name: str, value: Any) -> T | None:
        """根据指定字段获取单条记录。"""
        stmt = select(self.model).where(getattr(self.model, field_name) == value)
        return self.session.exec(stmt).first()

    def get_or_create(
        self, defaults: dict[str, Any] | None = None, **lookup: Any
    ) -> tuple[T, bool]:
        """按条件查找，不存在则创建。返回 (实例, 是否新建)。"""
        stmt = select(self.model)
        for name, value in lookup.items():
            stmt = stmt.where(getattr(self.model, name) == value)
        obj = self.session.exec(stmt).first()
        if obj is not None:
            return obj, False
        kwargs = {**lookup, **(defaults or {})}
        return self.create(**kwargs), True

    def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = True,
        **filters: Any,
    ) -> list[T]:
        """查询列表，支持过滤、排序、分页。"""
        stmt = self._apply_filters(select(self.model), **filters)

        if order_by:
            col = getattr(self.model, order_by, None)
            if col is not None:
                stmt = stmt.order_by(col.desc() if descending else col.asc())

        return list(self.session.exec(stmt.offset(offset).limit(limit)).all())

    def count(self, **filters: Any) -> int:
        """统计符合条件的记录数。"""
        stmt = self._apply_filters(
            select(func.count()).select_from(self.model), **filters
        )
        return self.session.exec(stmt).one()

    def paginate(self, *, limit: int = 100, offset: int = 0, **filters: Any) -> Page:
        """分页查询，同时返回总数和当前页数据。"""
        total = self.count(**filters)
        items = self.list(limit=limit, offset=offset, **filters)
        return Page(items=items, total=total, limit=limit, offset=offset)

    def exists(self, pk_value: Any) -> bool:
        """检查主键对应的记录是否存在。"""
        pk_cols = self._pk_columns()
        stmt = select(func.count()).select_from(self.model).where(pk_cols[0] == pk_value)
        return self.session.exec(stmt).one() > 0

    # ==================== 写入 ====================

    def create(self, **kwargs: Any) -> T:
        """创建新记录。"""
        obj = self.model(**kwargs)
        self.session.add(obj)
        self.session.flush()
        return obj

    def update(self, obj: T, **kwargs: Any) -> T:
        """更新记录的指定字段。"""
        valid = self._column_names()
        for key, value in kwargs.items():
            if key in valid:
                setattr(obj, key, value)
        if "updated_at" in valid and hasattr(obj, "updated_at"):
            obj.updated_at = datetime.now()
        self.session.add(obj)
        self.session.flush()
        return obj

    def save(self, obj: T) -> T:
        """保存（新增或更新）记录。"""
        self.session.add(obj)
        self.session.flush()
        return obj

    # ==================== 删除 ====================

    def delete(self, obj: T) -> None:
        """删除记录。"""
        self.session.delete(obj)
        self.session.flush()

    def delete_by_id(self, pk_value: Any) -> bool:
        """根据主键删除记录，返回是否成功删除。"""
        obj = self.get_by_id(pk_value)
        if obj is None:
            return False
        self.delete(obj)
        return True
