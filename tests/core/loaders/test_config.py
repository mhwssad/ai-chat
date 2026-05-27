"""测试 UnstructuredSettings 配置类。"""

from src.ai.config.loader_settings import UnstructuredSettings


class TestUnstructuredSettings:
    """测试 UnstructuredSettings。"""

    def test_default_values(self) -> None:
        settings = UnstructuredSettings()
        assert settings.api_key == ""
        assert settings.mode == "auto"
        assert settings.strategy == "fast"
        assert settings.max_characters == 1_000_000
        assert settings.chunking_strategy == ""
        assert settings.max_file_size == 100 * 1024 * 1024
        assert settings.languages == ["chi_sim", "eng"]

    def test_use_api_auto_mode_with_key(self) -> None:
        settings = UnstructuredSettings(mode="auto", api_key="test-key")
        assert settings.use_api is True

    def test_use_api_auto_mode_without_key(self) -> None:
        settings = UnstructuredSettings(mode="auto", api_key="")
        assert settings.use_api is False

    def test_use_api_explicit_api_mode(self) -> None:
        settings = UnstructuredSettings(mode="api", api_key="")
        assert settings.use_api is True

    def test_use_api_local_mode(self) -> None:
        settings = UnstructuredSettings(mode="local", api_key="some-key")
        assert settings.use_api is False

    def test_effective_chunking_strategy_empty(self) -> None:
        settings = UnstructuredSettings(chunking_strategy="")
        assert settings.effective_chunking_strategy is None

    def test_effective_chunking_strategy_set(self) -> None:
        settings = UnstructuredSettings(chunking_strategy="by_title")
        assert settings.effective_chunking_strategy == "by_title"

    def test_no_enabled_field(self) -> None:
        assert "enabled" not in UnstructuredSettings.model_fields

    def test_singleton_instance(self) -> None:
        from src.ai.config.loader_settings import unstructured_settings
        assert isinstance(unstructured_settings, UnstructuredSettings)
