"""
基础配置模块

包含 BaseSettingsConfig 基类和项目根目录路径定义
将基础配置与 AppConfig 分离，避免循环导入
"""

import sys
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

project_root: Path = Path(__file__).parent.parent.parent.parent
env_file_path: Path = project_root / ".env"  # 环境变量文件路径
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class BaseSettingsConfig(BaseSettings):
    """
    基础配置类，使用 pydantic v2 和 python-dotenv 来加载环境变量

    所有数据库配置类共享同一个 .env 文件，通过不同的环境变量前缀来区分。
    """

    model_config = SettingsConfigDict(
        env_file=env_file_path,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # 忽略额外的环境变量
    )

    def get_map(self) -> dict[str, str]:
        """
        获取字段名到环境变量名的映射

        通过检查子类中定义的 model_config.env_prefix 和所有字段，
        生成字段名与环境变量名的映射关系。

        Returns:
            字典，键为字段名，值为对应的环境变量名

        Example:
            >>> config = ValidationConfig()
            >>> mapping = config.get_map()
            >>> # {'enable_sql_validation': 'VALIDATION_ENABLE_SQL_VALIDATION', ...}
        """
        field_to_env_map: dict[str, str] = {}

        # 获取环境变量前缀（Pydantic v2 使用 model_config）
        env_prefix = self.__class__.model_config.get("env_prefix", "")

        # 遍历模型的所有字段（Pydantic v2 使用 model_fields）
        for field_name, field_info in self.__class__.model_fields.items():
            # 跳过私有字段
            if field_name.startswith("_"):
                continue

            # 优先使用 serialization_alias（Pydantic v2 序列化别名）
            if field_info.serialization_alias is not None:
                env_key = field_info.serialization_alias
            # 其次使用 validation_alias（Pydantic v2 验证别名）
            elif field_info.validation_alias is not None:
                # validation_alias 可能是字符串或字符串集合，转换为字符串
                env_key = str(field_info.validation_alias)
            # 使用默认格式：前缀+大写字段名
            else:
                env_key = f"{env_prefix}{field_name.upper()}"

            field_to_env_map[field_name] = env_key

        return field_to_env_map

    def refresh(self) -> None:
        """
        从环境变量重新加载配置

        此方法会重新从环境变量和 .env 文件中读取配置值，
        并更新当前实例的所有字段。当环境变量或 .env 文件
        被外部修改后，可以调用此方法来刷新配置。

        Example:
            >>> config = ValidationConfig()
            >>> config.some_field  # 原始值
            >>> # 修改 .env 文件或环境变量
            >>> config.refresh()  # 重新加载配置
            >>> config.some_field  # 新值
        """
        # 创建一个新的实例以重新加载环境变量
        new_instance = self.__class__()

        # 更新当前实例的所有字段
        for field_name in self.__class__.model_fields:
            if field_name.startswith("_"):
                continue
            # 使用 setattr 更新字段值
            setattr(self, field_name, getattr(new_instance, field_name))

    def save_to_env_file(self) -> None:
        """
        将当前配置保存到 .env 文件中

        此方法会读取现有的 .env 文件，更新或添加相应的环境变量，
        然后将修改后的内容写回文件。

        Raises:
            IOError: 当文件读写失败时抛出异常
        """
        # 定义字段与环境变量的映射
        field_to_env_map = self.get_map()
        # 读取现有 .env 文件内容
        env_content = ""
        if env_file_path.exists():
            env_content = env_file_path.read_text(encoding="utf-8")

        # 解析现有内容为行列表
        lines = env_content.split("\n")
        updated_lines = []
        processed_env_vars = set()

        # 遍历每一行，更新已有的环境变量
        for line in lines:
            stripped_line = line.strip()

            # 跳过空行和注释行
            if not stripped_line or stripped_line.startswith("#"):
                updated_lines.append(line)
                continue

            # 检查是否是需要更新的环境变量
            if "=" in stripped_line:
                env_key = stripped_line.split("=", 1)[0].strip()

                if env_key in field_to_env_map.values():
                    # 获取对应的字段名
                    field_name = next(
                        k for k, v in field_to_env_map.items() if v == env_key
                    )
                    # 更新该行
                    field_value = getattr(self, field_name)
                    updated_lines.append(f"{env_key}={field_value}")
                    processed_env_vars.add(env_key)
                else:
                    # 保留其他环境变量
                    updated_lines.append(line)
            else:
                updated_lines.append(line)

        # 添加缺失的环境变量（如果文件中不存在）
        for field_name, env_key in field_to_env_map.items():
            if env_key not in processed_env_vars:
                field_value = getattr(self, field_name)
                # 添加注释行和变量行
                updated_lines.append(f"\n# {field_to_env_map[field_name]}")
                updated_lines.append(f"{env_key}={field_value}")

        # 确保文件末尾有换行符
        if updated_lines and updated_lines[-1]:
            updated_lines.append("")

        # 写回 .env 文件
        env_file_path.write_text("\n".join(updated_lines), encoding="utf-8")


class BootstrapSettings(BaseSettingsConfig):
    """应用启动期最小配置。

    业务配置存储在数据库中；这里仅保留启动应用所必需的设置。
    """

    database_url: str = Field(default="", description="完整数据库连接 URL")
    database_path: str = Field(
        default=str(project_root / "data" / "app.db"),
        description="未设置 DATABASE_URL 时使用的 SQLite 数据库路径",
    )
    sqlalchemy_echo: bool = Field(default=False, description="是否输出 SQL 日志")
    encryption_key: str = Field(
        default="",
        description="Fernet 加密密钥，用于加密保存 API Key",
    )

    def resolved_database_url(self) -> str:
        """返回最终数据库 URL。"""
        if self.database_url.strip():
            return self.database_url.strip()

        db_path = Path(self.database_path)
        if not db_path.is_absolute():
            db_path = project_root / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path}"


@lru_cache(maxsize=1)
def get_bootstrap_settings() -> BootstrapSettings:
    """获取启动期配置单例。"""
    return BootstrapSettings()
