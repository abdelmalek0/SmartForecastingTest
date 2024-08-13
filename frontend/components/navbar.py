from fasthtml.common import *
from dataclasses import dataclass
from utils.ui_constants import navbar_item_style, toggled_style, no_decoration_style

@dataclass
class Navbar:
    """
    A class to represent the navigation bar with selectable menu items.

    Attributes:
        index (int): The index of the active navigation item.
    """

    index: int

    def __ft__(self) -> Div:
        """
        Renders the Navbar component.

        :return: A Div element containing the navigation bar.
        """
        # Helper function to create a navigation item with an optional toggled style.
        def nav_item(name: str, href: str, item_index: int) -> Div:
            is_toggled = self.index == item_index
            item_style = navbar_item_style + (toggled_style if is_toggled else "")
            return Div(
                A(
                    name, 
                    href=href, 
                    style=no_decoration_style
                ),
                style=item_style
            )

        return Div(
            Div(
                nav_item("Home", "/", 0),
                nav_item("Data sources", "/datasources", 1),
                nav_item("Data points", "/datapoints", 2),
                cls='flex flex-row justify-around w-[450px] h-[60px] \
                    bg-slate-100 rounded-full py-1'
            ),
            cls="flex flex-row justify-center items-center w-screen"
        )
