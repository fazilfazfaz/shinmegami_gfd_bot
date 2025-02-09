import asyncio
import time
from concurrent.futures import ProcessPoolExecutor
from math import floor
from multiprocessing import cpu_count

import cv2
import numpy as np

from logger import logger


def process_frame(frame):
    """
    Process a single frame to compute horizontal and vertical pixel changes.
    """
    frame_array = np.array(frame)

    horizontal_res = []
    vertical_res = []

    # Process horizontal changes
    for row in frame_array:
        changes = np.sum(np.any(row[:-1] != row[1:], axis=1))
        horizontal_res.append(changes)

    # Process vertical changes
    image_transposed = np.transpose(frame_array, (1, 0, 2))
    for y in range(image_transposed.shape[0]):
        vertical_pixels = image_transposed[y]
        changes = np.sum(np.any(vertical_pixels[:-1] != vertical_pixels[1:], axis=1))
        vertical_res.append(changes)

    # Calculate averages
    horizontal = np.floor(np.average(horizontal_res))
    vertical = np.floor(np.average(vertical_res))

    return horizontal, vertical


async def process_video(file_path: str, max_frames: int = 300, num_workers: int = None):
    """
    Process a video to compute average horizontal and vertical pixel changes.

    Parameters:
    - file_path (str): Path to the video file.
    - max_frames (int): Maximum number of frames to process.
    - num_workers (int): Number of worker processes to use. Defaults to CPU count.

    Returns:
    - (dict): A dictionary containing horizontal and vertical averages and percentages.
    """
    # Start timing
    start_time = time.time()

    # Open the video file
    cap = cv2.VideoCapture(file_path)

    # Validate the video file
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {file_path}")

    # Video properties
    original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    logger.info(f"Total Frames in the Video: {frame_count}")

    # Limit processing to max_frames if specified
    num_workers = min(cpu_count(), 16) if num_workers is None else num_workers
    logger.info(f"Using {num_workers} worker processes.")

    horizontal_results = []
    vertical_results = []

    # Use ProcessPoolExecutor for parallel frame processing
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        frames_to_process = []
        frame_counter = 0

        while frame_counter < max_frames:
            ret, frame = cap.read()
            if not ret or frame_counter >= max_frames:
                break

            frame_counter += 1
            frames_to_process.append(frame)

        # Submit frames to the executor and gather results asynchronously
        logger.info("Submitting frames to the process pool...")
        tasks = [executor.submit(process_frame, frame) for frame in frames_to_process]
        for task in asyncio.as_completed([asyncio.wrap_future(t) for t in tasks]):
            try:
                h, v = await task
                horizontal_results.append(h)
                vertical_results.append(v)
            except Exception as e:
                logger.error(f"Error processing frame: {e}")

    cap.release()  # Release video resource
    logger.info("Video processing complete.")

    # Compute final results
    horizontal_avg = floor(np.mean(horizontal_results) if horizontal_results else 0)
    vertical_avg = floor(np.mean(vertical_results) if vertical_results else 0)
    horizontal_percentage = floor((horizontal_avg / original_width * 100) if original_width else 0)
    vertical_percentage = floor((vertical_avg / original_height * 100) if original_height else 0)

    # Print timing information
    logger.info(f"Processing Complete in {time.time() - start_time:.2f} seconds")

    # Return results as a dictionary
    return {
        "horizontal_avg": horizontal_avg,
        "vertical_avg": vertical_avg,
        "horizontal_percentage": horizontal_percentage,
        "vertical_percentage": vertical_percentage,
        "original_width": original_width,
        "original_height": original_height,
    }
