from fasthtml.common import *
from components.navbar import Navbar
from components.badge import Badge, SEMANTIC_COLOR
from utils.constants import DATASOURCES_HEADERS, API_BASE_URL
from utils.helpers import fetch_datasources

def create_delete_button(datasource_id: int) -> Button:
    """
    Create a delete button with HTMX attributes for deleting a datasource.

    :param datasource_id: The ID of the datasource to be deleted.
    :return: A Button component configured for deletion.
    """
    return Button(
        "Delete",
        cls="btn btn-error btn-xs text-white",
        hx_delete=f"{API_BASE_URL}/datasources/{datasource_id}?htmx=1",
        hx_target="closest tr",
        hx_confirm="Are you sure you want to delete this datasource?",
        hx_swap="outerHTML"
    )

def create_details_button(datasource_id: int) -> A:
    """
    Create a details button that links to the datasource details page.

    :param datasource_id: The ID of the datasource.
    :return: An Anchor component linking to the details page.
    """
    return A(
        "Details",
        cls="btn btn-active btn-xs text-white",
        href=f"/datapoints/{datasource_id}?latest=200"
    )

def create_badge(content: str, color: SEMANTIC_COLOR) -> Badge:
    """
    Create a badge with the specified content and semantic color.

    :param content: The text content of the badge.
    :param color: The semantic color for the badge.
    :return: A Badge component with the given properties.
    """
    return Badge(content, color)

async def build_datasources_table(datasources: list) -> list:
    """
    Build a table of datasource rows from the provided list of datasources.

    :param datasources: A list of datasource dictionaries.
    :return: A list of Tr components representing the datasource rows.
    """
    result = []

    for data_source in datasources:
        datasource_id = data_source['id']
        datasource_name = data_source['datasource_info']['name']
        period_value = data_source['datasource_info']['period']['value']
        period_type = data_source['datasource_info']['period']['type']
        initialized_status = data_source['initialized']
        trained_status = data_source['trained']
        training_models = data_source['training']['models']

        period_badge = create_badge(f"{period_value} {period_type}", SEMANTIC_COLOR.INFO)
        model_badges = [create_badge(model, SEMANTIC_COLOR.SUCCESS) for model in training_models]

        row = Tr(
            Th(str(datasource_id)),
            Td(datasource_name),
            Td(period_badge),
            Td(initialized_status),
            Td(*model_badges),
            Td(trained_status),
            Td(
                create_details_button(datasource_id),
                create_delete_button(datasource_id)
            ),
            id=str(datasource_id)
        )
        result.append(row)

    return result

async def datasources(request: Request):
    """
    Render the datasources page with a table of available datasources.

    :param request: The Starlette request object.
    :return: A Div component containing the page layout.
    """
    datasources = await fetch_datasources()  # Assuming this should be an async call.

    return Div(
        Div(
            Navbar(index=1),
            Div(
                Table(
                    Thead(
                        Tr(
                            *[Th(header) for header in DATASOURCES_HEADERS]
                        ),
                        cls="bg-neutral text-white"
                    ),
                    Tbody(
                        *(await build_datasources_table(datasources))
                    ),
                    cls="table bg-gray-50"
                ),
                cls="p-5 w-screen"
            ),
            cls='flex flex-col items-start gap-2 items-center'
        )
    )
