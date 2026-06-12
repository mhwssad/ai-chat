"""沙箱执行环境 — 代码执行和文件操作在隔离环境中运行。

职责：
1. 支持 subprocess 隔离模式（最低可行方案）
2. 文件系统沙箱：限制可访问的目录白名单
3. 网络沙箱：限制可访问的域名/IP 白名单
4. 资源限制：超时、最大内存、最大输出长度
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from src.ai.config.logging_setup import get_logger
from src.ai.exception.tool_exception import ToolExecutionError

logger = get_logger(__name__)


@dataclass
class SandboxConfig:
    """沙箱配置。

    Attributes:
        allowed_dirs: 允许访问的目录白名单（空列表表示不限制）。
        blocked_dirs: 禁止访问的目录黑名单。
        allowed_domains: 允许网络访问的域名白名单（空列表表示不限制）。
        timeout: 执行超时秒数。
        max_output_bytes: 最大输出字节数。
        max_memory_mb: 最大内存使用（MB，subprocess 模式）。
    """

    allowed_dirs: list[str] = field(default_factory=list)
    blocked_dirs: list[str] = field(
        default_factory=lambda: [
            "/etc",
            "/sys",
            "/proc",
            "C:\\Windows\\System32",
        ]
    )
    allowed_domains: list[str] = field(default_factory=list)
    timeout: float = 30.0
    max_output_bytes: int = 1_000_000  # 1 MB
    max_memory_mb: int = 256


class FileSystemSandbox:
    """文件系统沙箱 — 检查路径是否在允许范围内。

    Args:
        config: 沙箱配置。
    """

    def __init__(self, config: SandboxConfig) -> None:
        self._config = config
        # 规范化白名单路径
        self._allowed_paths = [
            Path(d).resolve() for d in config.allowed_dirs
        ]
        self._blocked_paths = [
            Path(d).resolve() for d in config.blocked_dirs
        ]

    def is_path_allowed(self, path: str | Path) -> bool:
        """检查路径是否在允许范围内。

        Args:
            path: 待检查的路径。

        Returns:
            True 表示路径被允许访问。
        """
        try:
            resolved = Path(path).resolve()
        except (OSError, ValueError):
            return False

        # 检查黑名单
        for blocked in self._blocked_paths:
            try:
                resolved.relative_to(blocked)
                return False
            except ValueError:
                pass

        # 白名单为空表示不限制
        if not self._allowed_paths:
            return True

        # 检查白名单
        for allowed in self._allowed_paths:
            try:
                resolved.relative_to(allowed)
                return True
            except ValueError:
                pass

        return False

    def validate_path(self, path: str | Path) -> Path:
        """验证路径并返回解析后的绝对路径。

        Args:
            path: 待验证的路径。

        Returns:
            解析后的绝对路径。

        Raises:
            ToolExecutionError: 路径不在允许范围内。
        """
        resolved = Path(path).resolve()
        if not self.is_path_allowed(resolved):
            raise ToolExecutionError(
                f"沙箱限制：路径 {resolved} 不在允许范围内",
                context={"path": str(resolved)},
            )
        return resolved


class NetworkSandbox:
    """网络沙箱 — 检查域名是否在允许范围内。

    Args:
        config: 沙箱配置。
    """

    def __init__(self, config: SandboxConfig) -> None:
        self._config = config
        self._allowed = set(config.allowed_domains)

    def is_domain_allowed(self, domain: str) -> bool:
        """检查域名是否在允许范围内。

        Args:
            domain: 待检查的域名。

        Returns:
            True 表示域名被允许访问。
        """
        if not self._allowed:
            return True  # 空白名单表示不限制

        domain_lower = domain.lower()
        for allowed in self._allowed:
            if domain_lower == allowed.lower() or domain_lower.endswith(
                f".{allowed.lower()}"
            ):
                return True
        return False

    def validate_url(self, url: str) -> str:
        """验证 URL 的域名是否在允许范围内。

        Args:
            url: 待验证的 URL。

        Returns:
            验证通过的 URL。

        Raises:
            ToolExecutionError: 域名不在允许范围内。
        """
        if not self._allowed:
            return url

        # 简单提取域名
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            hostname = parsed.hostname or ""
        except Exception:
            hostname = ""

        if hostname and not self.is_domain_allowed(hostname):
            raise ToolExecutionError(
                f"沙箱限制：域名 {hostname} 不在允许范围内",
                context={"domain": hostname, "url": url},
            )
        return url


class SubprocessSandbox:
    """子进程沙箱 — 在隔离的子进程中执行命令。

    最低可行方案：使用 subprocess 隔离执行环境。

    Args:
        config: 沙箱配置。
    """

    def __init__(self, config: SandboxConfig) -> None:
        self._config = config
        self._fs = FileSystemSandbox(config)
        self._net = NetworkSandbox(config)

    async def run(
        self,
        command: list[str],
        *,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """在沙箱子进程中执行命令。

        Args:
            command: 命令和参数列表。
            cwd: 工作目录。
            env: 额外环境变量。

        Returns:
            子进程执行结果。

        Raises:
            ToolExecutionError: 路径验证失败或执行超时。
        """
        # 验证工作目录
        if cwd:
            self._fs.validate_path(cwd)

        # 构建安全环境变量（不继承敏感变量）
        safe_env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith(
                ("API_", "SECRET_", "TOKEN_", "KEY_", "PASSWORD_", "CREDENTIAL")
            )
        }
        if env:
            safe_env.update(env)

        try:
            result = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=safe_env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    result.communicate(),
                    timeout=self._config.timeout,
                )
            except TimeoutError:
                result.kill()
                raise ToolExecutionError(
                    f"沙箱执行超时 ({self._config.timeout}s)",
                    context={"command": " ".join(command)},
                )

            # 截断过大输出
            stdout_str = stdout[: self._config.max_output_bytes].decode(
                "utf-8", errors="replace"
            )
            stderr_str = stderr[: self._config.max_output_bytes].decode(
                "utf-8", errors="replace"
            )

            return subprocess.CompletedProcess(
                args=command,
                returncode=result.returncode or 0,
                stdout=stdout_str,
                stderr=stderr_str,
            )

        except ToolExecutionError:
            raise
        except Exception as e:
            raise ToolExecutionError(
                f"沙箱子进程执行异常: {e}",
                context={"command": " ".join(command)},
            )

    @property
    def fs(self) -> FileSystemSandbox:
        """文件系统沙箱实例。"""
        return self._fs

    @property
    def net(self) -> NetworkSandbox:
        """网络沙箱实例。"""
        return self._net


class SandboxExecutor:
    """沙箱执行器 — 统一入口。

    根据工具的 requires_sandbox 标志和全局配置决定是否使用沙箱。

    Args:
        config: 沙箱配置。
    """

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self._config = config or SandboxConfig()
        self._subprocess = SubprocessSandbox(self._config)
        self._fs = FileSystemSandbox(self._config)
        self._net = NetworkSandbox(self._config)

    @property
    def subprocess(self) -> SubprocessSandbox:
        """子进程沙箱实例。"""
        return self._subprocess

    @property
    def fs(self) -> FileSystemSandbox:
        """文件系统沙箱实例。"""
        return self._fs

    @property
    def net(self) -> NetworkSandbox:
        """网络沙箱实例。"""
        return self._net

    @property
    def config(self) -> SandboxConfig:
        """沙箱配置。"""
        return self._config
