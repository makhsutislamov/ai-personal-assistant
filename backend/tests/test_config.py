import stat

from app.core.config import ConfigManager
from app.models.schemas import AzureOpenAISettings, OllamaSettings, SettingsSchema


class TestConfigManager:
    def test_load_defaults_when_no_file(self, tmp_path):
        manager = ConfigManager(config_dir=tmp_path)
        settings = manager.load()
        assert settings == SettingsSchema()

    def test_save_and_load_roundtrip(self, tmp_path):
        manager = ConfigManager(config_dir=tmp_path)
        original = SettingsSchema(
            llm_provider="azure_openai",
            ollama=OllamaSettings(base_url="http://custom:11434", model="llama3.2"),
            azure_openai=AzureOpenAISettings(
                endpoint="https://myaccount.openai.azure.com/",
                api_key="super-secret",
                deployment="gpt-4o",
                api_version="2024-06-01",
            ),
        )
        manager.save(original)
        loaded = manager.load()
        assert loaded == original

    def test_file_permissions(self, tmp_path):
        manager = ConfigManager(config_dir=tmp_path)
        manager.save(SettingsSchema())
        path = manager.get_settings_path()
        file_mode = stat.S_IMODE(path.stat().st_mode)
        assert file_mode == 0o600

    def test_get_settings_path(self, tmp_path):
        manager = ConfigManager(config_dir=tmp_path)
        path = manager.get_settings_path()
        assert path.name == "settings.json"
        assert path.parent == tmp_path

    def test_load_returns_defaults_on_corrupt_file(self, tmp_path):
        manager = ConfigManager(config_dir=tmp_path)
        settings_path = manager.get_settings_path()
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text("{{not valid json}}", encoding="utf-8")
        settings = manager.load()
        assert settings == SettingsSchema()

    def test_save_creates_parent_directories(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        manager = ConfigManager(config_dir=nested)
        manager.save(SettingsSchema())
        assert manager.get_settings_path().exists()
