import logging
import ijson
import aiofiles
import asyncio
from watchdog.events import FileSystemEventHandler

# Configure logging to display timestamps, log level, and messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define batch size for processing JSON data
BATCH_SIZE = 1000  # Adjust the batch size based on your memory and performance requirements

class NewFileHandler(FileSystemEventHandler):
    def __init__(self, db, loop):
        """
        Initialize the NewFileHandler with a database connection and event loop.

        :param db: Database instance for interacting with the PostgreSQL database.
        :param loop: Event loop to schedule asynchronous tasks.
        """
        self.db = db
        self.loop = loop  # Pass the running event loop from the main application

    def on_created(self, event):
        """
        Handle the event when a new file is created in the monitored directory.

        :param event: Event object containing information about the created file.
        """
        if not event.is_directory:
            # Schedule the process_file coroutine on the running event loop
            self.loop.create_task(self.process_file(event.src_path))

    async def process_file(self, file_path):
        """
        Determine the type of the file and process it accordingly.

        :param file_path: Path to the newly created file.
        """
        if 'objects_detection' in file_path:
            await self.process_objects_detection(file_path)
        elif 'vehicles_status' in file_path:
            await self.process_vehicles_status(file_path)

    async def process_objects_detection(self, file_path):
        """
        Process the objects detection JSON file in batches and insert data into the database.

        :param file_path: Path to the objects detection JSON file.
        """
        try:
            # Open the file asynchronously
            async with aiofiles.open(file_path, 'r') as file:
                # Parse JSON items incrementally using ijson
                objects = ijson.items(file, 'objects_detection_events.item')
                batch = []
                async for obj in objects:
                    # Append each object to the batch
                    batch.append((obj['vehicle_id'], obj['detection_time'], obj['object_type'], obj['object_value']))
                    if len(batch) >= BATCH_SIZE:
                        # Insert the batch into the database
                        await self.db.insert_objects_detection(batch)
                        batch = []
                if batch:
                    # Insert any remaining items in the last batch
                    await self.db.insert_objects_detection(batch)
        except (ijson.JSONError, KeyError) as e:
            logging.error("Error processing objects detection file %s: %s", file_path, e)
        except Exception as e:
            logging.error("Unexpected error processing objects detection file %s: %s", file_path, e)

    async def process_vehicles_status(self, file_path):
        """
        Process the vehicles status JSON file in batches and insert data into the database.

        :param file_path: Path to the vehicles status JSON file.
        """
        try:
            # Open the file asynchronously
            async with aiofiles.open(file_path, 'r') as file:
                # Parse JSON items incrementally using ijson
                statuses = ijson.items(file, 'vehicle_status.item')
                batch = []
                async for status in statuses:
                    # Append each status to the batch
                    batch.append((status['vehicle_id'], status['report_time'], status['status']))
                    if len(batch) >= BATCH_SIZE:
                        # Insert the batch into the database
                        await self.db.insert_vehicle_status(batch)
                        batch = []
                if batch:
                    # Insert any remaining items in the last batch
                    await self.db.insert_vehicle_status(batch)
        except (ijson.JSONError, KeyError) as e:
            logging.error("Error processing vehicles status file %s: %s", file_path, e)
        except Exception as e:
            logging.error("Unexpected error processing vehicles status file %s: %s", file_path, e)

