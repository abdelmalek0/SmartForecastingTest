from fasthtml.common import *
from dataclasses import dataclass
from typing import List, Dict, Union

@dataclass
class Pagination:
    total_number_pages: int
    current_page: int
    base_path: str
    params: Dict[str, Union[str, int]] = None

    def __post_init__(self):
        if self.params is None:
            self.params = {}

    def get_visible_pages(self) -> List[Union[int, None]]:
        if self.total_number_pages <= 5:
            return list(range(1, self.total_number_pages + 1))

        if self.current_page < 4:
            return list(range(1, 5)) + [None, self.total_number_pages] if self.total_number_pages > 5 else [self.total_number_pages]

        if self.current_page > self.total_number_pages - 3:
            return [1, None] + list(range(self.total_number_pages - 3, self.total_number_pages + 1))

        return [1, None, self.current_page - 1, self.current_page, self.current_page + 1, None, self.total_number_pages]

    def build_redirection_path(self, page: int) -> str:
        filtered_params = {**self.params, 'page': page}
        filtered_query_string = '&'.join(f"{key}={value}" for key, value in filtered_params.items() if value is not None)
        return f'{self.base_path}?{filtered_query_string}'

    def __ft__(self) -> Div:
        pages_to_show = self.get_visible_pages()
        pagination_items = [
            Input(
                name="options",
                cls=f"join-item btn {'btn-disabled' if page is None else ''}",
                type="radio",
                checked="checked" if self.current_page == page else None,
                onclick=f"window.location.href='{self.build_redirection_path(page)}'",
                aria_label=str(page) if page is not None else "..."
            )
            for page in pages_to_show
        ]
        return Div(*pagination_items, cls="join")
