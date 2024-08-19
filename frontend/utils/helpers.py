import requests
from utils.constants import API_BASE_URL

def get_visible_pages(number_pages, current_page):
    """
    Determine which pages to show in the pagination component.
    
    :param number_pages: Total number of pages.
    :param current_page: Current page number.
    :return: List of pages to display.
    """
    pages = list(range(1, number_pages + 1))
    
    if number_pages < 5:
        return pages
    
    if current_page < 4:
        return pages[:4] + ([None, number_pages] if number_pages > 5 else [number_pages])
    
    if current_page > (number_pages - 3):
        return [1] + ([None] if 1 < (number_pages - 4) else []) + pages[-4:]
        
    return [1, None, current_page - 1, current_page, current_page + 1, None, number_pages]

async def fetch_datasources() -> list:
    """
    Fetch all data sources from the data source handler.

    :return: List of data sources.
    """
    response = requests.get(f'{API_BASE_URL}/datasources/all')
    
    return response.json()

async def fetch_datapoints(datasource_id: int, 
                           start_date: str | None, end_date: str | None,
                           latest: int | None,
                           page: int | None, per_page: int = 15):
    
    endpoint = f'{API_BASE_URL}/datasources/{datasource_id}/datapoints/all'
    params = {"page": page, "per_page": per_page, 
              'start_date': start_date, 'end_date': end_date,
              'latest': latest}
    response = requests.get(endpoint, params=params)
    
    return response.json()