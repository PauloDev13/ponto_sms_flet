class PageManager:
    _page_instance = None

    @classmethod
    def set_page(cls, page):
        cls._page_instance = page

    @classmethod
    def get_page(cls):
        if cls._page_instance is None:
            raise ValueError('Instãncia de Page indefinida')

        return cls._page_instance
