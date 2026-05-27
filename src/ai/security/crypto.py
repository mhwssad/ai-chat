"""敏感数据加密工具。

使用 Fernet 对 API Key 等敏感信息做认证加密后再入库。
没有配置加密密钥时会直接报错，避免误把明文写入数据库。

用法::

    from src.ai.security.crypto import encrypt_secret, decrypt_secret, generate_key

    # 生成密钥，写入环境变量 ENCRYPTION_KEY
    key = generate_key()

    cipher = encrypt_secret("sk-abc123")
    plain = decrypt_secret(cipher)
"""


from src.ai.config.base_config import get_bootstrap_settings
from src.ai.config.logging_setup import get_logger

logger = get_logger(__name__)

_fernet = None
_TOKEN_PREFIX = "fernet:"


def _get_fernet():
    """获取 Fernet 实例。"""
    global _fernet

    if _fernet is not None:
        return _fernet

    key = get_bootstrap_settings().encryption_key.strip()
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY 未配置，拒绝保存明文敏感信息。"
            "请先调用 generate_key() 生成密钥并写入环境变量。"
        )

    try:
        from cryptography.fernet import Fernet

        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as e:
        logger.error("Fernet 初始化失败: %s", e)
        raise RuntimeError("ENCRYPTION_KEY 无效，无法初始化加密引擎") from e

    return _fernet


def encrypt_secret(plaintext: str) -> str:
    """加密敏感字符串。

    返回值带有 ``fernet:`` 前缀，便于后续区分是否已加密。
    """
    if not plaintext:
        return plaintext

    if plaintext.startswith(_TOKEN_PREFIX):
        return plaintext

    token = _get_fernet().encrypt(plaintext.encode()).decode()
    return f"{_TOKEN_PREFIX}{token}"


def decrypt_secret(ciphertext: str) -> str:
    """解密敏感字符串。"""
    if not ciphertext:
        return ciphertext

    token = ciphertext
    if ciphertext.startswith(_TOKEN_PREFIX):
        token = ciphertext.removeprefix(_TOKEN_PREFIX)

    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except Exception as e:
        logger.error("解密失败: %s", e)
        raise ValueError("解密失败：密钥不匹配或数据已损坏") from e


def encrypt(plaintext: str) -> str:
    """兼容旧调用的加密函数。"""
    return encrypt_secret(plaintext)


def decrypt(ciphertext: str) -> str:
    """兼容旧调用的解密函数。"""
    return decrypt_secret(ciphertext)


def generate_key() -> str:
    """生成新的 Fernet 密钥。"""
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode()
