import logging
import os

# Define the log directory and ensure it exists
log_dir = '/home/debian/SmartForecasting/logs'
os.makedirs(log_dir, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Output to console
        logging.FileHandler(os.path.join(log_dir, 'app.log'))  # Output to file
    ]
)

# Create a logger instance
logger = logging.getLogger('SmartForecastingLogger')
