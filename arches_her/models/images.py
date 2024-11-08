class Image:
    def __init__(self, url: str, caption: str, copyright: str):
        self.url = url
        self.caption = caption
        self.copyright = copyright

    def __str__(self):
        return f"Image(url={self.url}, caption={self.caption}, copyright={self.copyright})"
