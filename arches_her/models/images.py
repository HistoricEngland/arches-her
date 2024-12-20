from arches.app.models.system_settings import settings

class SettingsSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsSingleton, cls).__new__(cls)
            cls._instance.ARCHES_NAMESPACE_FOR_DATA_EXPORT = settings.ARCHES_NAMESPACE_FOR_DATA_EXPORT
        return cls._instance


class Image:
    def __init__(self, url: str, caption: str, copyright: str):
        settings_singleton = SettingsSingleton()
        self.url = f"{settings_singleton.ARCHES_NAMESPACE_FOR_DATA_EXPORT}{url}"
        self.caption = caption
        self.copyright = copyright

    def __str__(self):
        return f"Image(url={self.url}, caption={self.caption}, copyright={self.copyright})"
