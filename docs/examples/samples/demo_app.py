"""示例应用模块 — 展示代码切割效果。"""


from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class UserModel:
    """用户数据模型。"""

    id: int
    name: str
    email: str
    active: bool = True

    def display_name(self) -> str:
        """获取显示名称。"""
        return self.name if self.active else f"[已停用] {self.name}"


class UserService:
    """用户服务 — 处理用户相关业务逻辑。"""

    def __init__(self, *, database_path: str = "users.db") -> None:
        self._db_path = Path(database_path)
        self._users: dict[int, UserModel] = {}
        self._next_id = 1

    def create_user(self, name: str, email: str) -> UserModel:
        """创建新用户。

        Args:
            name: 用户名。
            email: 电子邮件。

        Returns:
            UserModel: 创建的用户对象。
        """
        user = UserModel(id=self._next_id, name=name, email=email)
        self._users[user.id] = user
        self._next_id += 1
        return user

    def get_user(self, user_id: int) -> UserModel | None:
        """根据 ID 查找用户。"""
        return self._users.get(user_id)

    def deactivate(self, user_id: int) -> bool:
        """停用用户。"""
        user = self._users.get(user_id)
        if user is None:
            return False
        self._users[user_id] = UserModel(
            id=user.id, name=user.name, email=user.email, active=False,
        )
        return True

    def list_active(self) -> list[UserModel]:
        """列出所有活跃用户。"""
        return [u for u in self._users.values() if u.active]


class ReportGenerator:
    """报表生成器。"""

    def __init__(self, user_service: UserService) -> None:
        self._service = user_service

    def generate_summary(self) -> dict[str, Any]:
        """生成用户摘要报表。"""
        all_users = list(self._service._users.values())
        active = self._service.list_active()
        return {
            "total": len(all_users),
            "active": len(active),
            "inactive": len(all_users) - len(active),
        }
