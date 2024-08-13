from typing import Final

APP_NAME: Final = 'SmartForecasting'
APP_DESCRIPTION: Final = 'Welcome to SmartForecasting! This cutting-edge service \
                is designed to forecast product consumption and sales trends, \
                empowering businesses to make data-driven decisions and stay \
                ahead of the competition.'
                
COPYRIGHTS: Final = 'Copyright © 2024 - All right reserved by SmartPrintsKSA'

DATASOURCES_HEADERS: Final = ['ID', 'Name', 'Period', 'Init', 'Models', 'Trained', 'Action']
DATAPOINTS_HEADERS: Final = ['ID', 'Date', 'Value', 'AutoReg', 'ExpSmoothing']

API_BASE_URL: Final = 'http://51.178.17.47:8000/api/v1'