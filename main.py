"""AI Chat 统一入口 — 支持优雅退出和信号处理。"""

from __future__ import annotations

import asyncio
import atexit
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

_src = str(Path(__file__).resolve().parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

import click
import uvicorn

# 初始化日志系统 — 必须在其他模块导入前调用
from src.ai.config.logging_setup import setup_logging
setup_logging()

# uvicorn 日志配置 — 继承默认配置但不覆盖已有 logger
import copy as _copy
import uvicorn.config as _uvicorn_config
_uvicorn_log_config = _copy.deepcopy(_uvicorn_config.LOGGING_CONFIG)
_uvicorn_log_config["disable_existing_loggers"] = False

# 前端项目目录
_FRONT_DIR = Path(__file__).resolve().parent / "src" / "front" / "ai-chat"

# -- 全局关闭状态 --
_shutdown_initiated = False
_shutdown_start_time: float = 0.0
_graceful_timeout: int = 10
_front_proc: subprocess.Popen | None = None

# 需要清理的资源引用（被 atexit 和信号处理器使用）
_pending_cleanup: list[tuple[str, callable]] = []


def _register_cleanup(name: str, fn: callable) -> None:
    """注册清理回调，按注册顺序逆序执行。"""
    _pending_cleanup.append((name, fn))


def _print_shutdown(msg: str) -> None:
    """统一格式的关闭日志输出。"""
    elapsed = time.monotonic() - _shutdown_start_time if _shutdown_start_time else 0
    click.echo(f"  [{elapsed:.1f}s] {msg}", err=True)


# -- 前端进程管理 --


def _start_frontend(port: int) -> subprocess.Popen:
    """启动前端 Vite 开发服务器，返回子进程对象。"""
    cmd = "pnpm dev --port " + str(port)
    proc = subprocess.Popen(
        cmd,
        shell=True,
        cwd=str(_FRONT_DIR),
        stdin=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    click.echo(f"前端开发服务器已启动 (PID: {proc.pid}, 端口: {port})")
    return proc


def _stop_frontend(proc: subprocess.Popen) -> None:
    """停止前端开发服务器及其子进程。"""
    if proc is None or proc.poll() is not None:
        return
    _print_shutdown("停止前端开发服务器...")
    if sys.platform == "win32":
        try:
            proc.send_signal(signal.CTRL_BREAK_EVENT)
            try:
                proc.wait(timeout=2)
                _print_shutdown("前端开发服务器已停止")
                return
            except subprocess.TimeoutExpired:
                pass
        except Exception:
            pass
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=3,
            )
        except (subprocess.TimeoutExpired, Exception):
            pass
    else:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    _print_shutdown("前端开发服务器已停止")


# -- 信号处理 --


def _do_exit(code: int = 0) -> None:
    """执行最终清理并强制退出进程。

    在 os._exit() 之前必须先杀掉前端子进程，否则孤儿进程会占用终端。
    所有 os._exit() 路径都必须经过此函数。
    """
    # 停止前端（带超时保护）
    if _front_proc is not None and _front_proc.poll() is None:
        if sys.platform == "win32":
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(_front_proc.pid)],
                    capture_output=True,
                    timeout=3,
                )
            except Exception:
                pass
        else:
            try:
                _front_proc.kill()
            except Exception:
                pass

    # 刷缓冲，确保退出消息可见
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass

    os._exit(code)


def _signal_handler(signum: int, _frame) -> None:
    """信号处理器 -- 只在第一次触发时标记关闭，第二次强制退出。"""
    import threading

    global _shutdown_initiated, _shutdown_start_time
    if _shutdown_initiated:
        click.echo("\n再次收到信号，强制退出！", err=True)
        _do_exit(1)

    _shutdown_initiated = True
    _shutdown_start_time = time.monotonic()
    signame = signal.Signals(signum).name
    click.echo(f"\n收到 {signame}，开始优雅退出...", err=True)

    # 看门狗：无论优雅退出是否完成，超时后强制终止
    def _watchdog() -> None:
        time.sleep(_graceful_timeout + 2)
        click.echo("\n优雅退出超时，强制终止进程！", err=True)
        _do_exit(1)

    threading.Thread(target=_watchdog, daemon=True, name="shutdown-watchdog").start()


# -- 清理逻辑 --


def _run_shutdown_cleanup() -> None:
    """执行所有注册的清理回调。"""
    global _pending_cleanup

    if not _pending_cleanup:
        return

    _print_shutdown("执行资源清理...")
    for name, fn in reversed(_pending_cleanup):
        try:
            _print_shutdown(f"清理: {name}")
            fn()
        except Exception as e:
            _print_shutdown(f"清理失败 [{name}]: {e}")

    _pending_cleanup.clear()
    _print_shutdown("资源清理完成")


# -- atexit 兜底 --

def _atexit_handler() -> None:
    """进程正常退出时兜底清理（os._exit 会跳过此回调）。"""
    if _front_proc is not None and _front_proc.poll() is None:
        _print_shutdown("atexit: 停止前端进程...")
        _stop_frontend(_front_proc)


atexit.register(_atexit_handler)


# -- 服务启动（后端优先，前端后启） --


def _run_server_then_front(
    host: str,
    port: int,
    front: bool,
    front_port: int,
    graceful_timeout: int,
) -> None:
    """正常模式：先启动后端，就绪后启动前端。"""
    global _front_proc
    config = uvicorn.Config(
        "src.ai.api:app",
        host=host,
        port=port,
        reload=False,
        log_config=_uvicorn_log_config,
    )
    server = uvicorn.Server(config)

    async def _serve() -> None:
        serve_task = asyncio.ensure_future(server.serve())

        # 等待后端就绪
        await asyncio.sleep(0.5)
        while not server.started:
            await asyncio.sleep(0.1)
        click.echo(f"后端 API 已启动 (http://{host}:{port})")

        # 后端就绪后再启动前端
        if front:
            if not _FRONT_DIR.is_dir():
                click.echo(f"错误: 前端目录不存在 {_FRONT_DIR}", err=True)
                sys.exit(1)
            _front_proc = _start_frontend(front_port)

        # 等待关闭信号
        while not _shutdown_initiated and not serve_task.done():
            await asyncio.sleep(0.1)

        if not serve_task.done():
            _print_shutdown("通知 uvicorn 停止接受新请求...")
            server.should_exit = True
            try:
                await asyncio.wait_for(serve_task, timeout=graceful_timeout)
            except asyncio.TimeoutError:
                _print_shutdown(f"uvicorn 未在 {graceful_timeout}s 内关闭，取消任务...")
                serve_task.cancel()
                try:
                    await serve_task
                except (asyncio.CancelledError, Exception):
                    pass
            except asyncio.CancelledError:
                pass
        else:
            exc = serve_task.exception()
            if exc:
                click.echo(f"服务异常退出: {exc}", err=True)

        # ── 关键：在 asyncio.run() 清理之前完成所有收尾 ──
        # asyncio.run() 的清理（shutdown_default_executor）可能永久挂住，
        # 所以这里直接做完清理后 os._exit()，不给它机会。
        if _front_proc is not None:
            _stop_frontend(_front_proc)
            _front_proc = None
        _run_shutdown_cleanup()
        elapsed = time.monotonic() - _shutdown_start_time if _shutdown_start_time else 0
        click.echo(f"\nAI Chat 已关闭 (耗时 {elapsed:.1f}s)")
        _do_exit(0)

    try:
        asyncio.run(_serve())
    except KeyboardInterrupt:
        pass
    # 注意：没有 finally — 清理和 os._exit 都在 _serve() 内部完成
    # 如果 _serve() 异常退出（不应该发生），看门狗会兜底


def _run_reload_then_front(
    host: str,
    port: int,
    front: bool,
    front_port: int,
    graceful_timeout: int,
) -> None:
    """reload 模式：先启动后端（线程），就绪后启动前端。"""
    import threading

    config = uvicorn.Config(
        "src.ai.api:app",
        host=host,
        port=port,
        reload=True,
        log_config=_uvicorn_log_config,
    )
    server = uvicorn.Server(config)

    server_thread = threading.Thread(
        target=server.run,
        name="uvicorn-reload",
        daemon=False,
    )
    server_thread.start()

    # 等待后端就绪
    time.sleep(0.5)
    while not server.started:
        time.sleep(0.1)
    click.echo(f"后端 API 已启动 (http://{host}:{port})")

    # 后端就绪后再启动前端
    global _front_proc
    if front:
        if not _FRONT_DIR.is_dir():
            click.echo(f"错误: 前端目录不存在 {_FRONT_DIR}", err=True)
            sys.exit(1)
        _front_proc = _start_frontend(front_port)

    try:
        while server_thread.is_alive():
            server_thread.join(timeout=0.5)
            if _shutdown_initiated:
                server.should_exit = True
                deadline = time.monotonic() + graceful_timeout
                while server_thread.is_alive() and time.monotonic() < deadline:
                    server_thread.join(timeout=0.5)
                if server_thread.is_alive():
                    click.echo(f"\n服务未在 {graceful_timeout}s 内关闭，强制退出", err=True)
                break
    finally:
        if _front_proc is not None:
            _stop_frontend(_front_proc)
            _front_proc = None
        _run_shutdown_cleanup()
        elapsed = time.monotonic() - _shutdown_start_time if _shutdown_start_time else 0
        click.echo(f"\nAI Chat 已关闭 (耗时 {elapsed:.1f}s)")
        _do_exit(0)


# -- CLI --


@click.command()
@click.option("--host", default="127.0.0.1", help="监听地址")
@click.option("--port", default=8000, help="后端监听端口")
@click.option("--reload", is_flag=True, default=False, help="启用后端热重载")
@click.option("--front", is_flag=True, default=False, help="同时启动前端开发服务器")
@click.option("--front-port", default=5173, help="前端开发服务器端口")
@click.option(
    "--graceful-timeout",
    default=10,
    type=int,
    help="优雅关闭超时时间(秒，默认 10)",
)
def main(
    host: str,
    port: int,
    reload: bool,
    front: bool,
    front_port: int,
    graceful_timeout: int,
) -> None:
    """AI Chat -- 本地 AI 工作台

    启动顺序：后端先启动，就绪后再启动前端。
    """
    global _front_proc, _graceful_timeout
    _graceful_timeout = graceful_timeout

    click.echo("=" * 50)
    click.echo("AI Chat -- 本地 AI 工作台")
    click.echo(f"优雅关闭超时: {graceful_timeout}s")
    click.echo("=" * 50)
    click.echo()

    # 注册信号处理器
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, _signal_handler)

    # 先启动后端，再启动前端
    if reload:
        _run_reload_then_front(host, port, front, front_port, graceful_timeout)
    else:
        _run_server_then_front(host, port, front, front_port, graceful_timeout)


if __name__ == "__main__":
    main()
