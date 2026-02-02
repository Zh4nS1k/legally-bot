import os
import logging
import datetime

def get_next_run_count(logs_dir="logs"):
    """
    Reads the current run count from .run_count file, increments it, and returns it.
    """
    count_file = os.path.join(logs_dir, ".run_count")
    
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        
    count = 0
    if os.path.exists(count_file):
        try:
            with open(count_file, "r") as f:
                count = int(f.read().strip())
        except ValueError:
            count = 0
            
    count += 1
    
    with open(count_file, "w") as f:
        f.write(str(count))
        
    return count

def setup_logging():
    """
    Configures logging with dynamic filenames:
    - run_XXX_DD_MM_YYYY_HH_MM.log
    - error_XXX_DD_MM_YYYY_HH_MM.log
    """
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    run_count = get_next_run_count(logs_dir)
    now = datetime.datetime.now()
    timestamp = now.strftime("%d_%m_%Y_%H_%M")
    
    run_count_str = f"{run_count:03d}"
    
    log_filename = f"run_{run_count_str}_{timestamp}.log"
    error_filename = f"error_{run_count_str}_{timestamp}.log"
    
    log_path = os.path.join(logs_dir, log_filename)
    error_path = os.path.join(logs_dir, error_filename)

    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # 1. Stream Handler (Console)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    # 2. Main File Handler (All logs)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    
    # 3. Error File Handler (Only Errors)
    err_handler = logging.FileHandler(error_path, encoding="utf-8")
    err_handler.setFormatter(formatter)
    err_handler.setLevel(logging.ERROR)
    logger.addHandler(err_handler)
    
    logging.info(f"📝 Logging setup complete. Log file: {log_filename}")
    logging.info(f"📝 Error log file: {error_filename}")
