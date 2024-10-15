# app/database/__init__.py

from .connection import db 
from .models import Spreadsheet, SpreadsheetRow, Instance, SpreadsheetInstance
from .data_extraction import data_extractor
from .data_insertion import insert_data_to_db
from .instance_handling import find_instances, insert_instances_to_db
from .filtering import get_tables, get_instances, get_columns
import logging

logging.basicConfig(
        level=logging.DEBUG,  # Set to DEBUG for detailed logs; change to INFO or WARNING in production
        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
logger = logging.getLogger(__name__)

