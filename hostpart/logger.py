import logging
import logging.handlers

def logger(log_path):
    log = logging.getLogger('snowdeer_log')
    log.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter('[%(levelname)s] (%(filename)s:%(lineno)d) > %(message)s')
    
    fileHandler = logging.FileHandler(log_path)
    streamHandler = logging.StreamHandler()
    
    fileHandler.setFormatter(formatter)
    streamHandler.setFormatter(formatter)
    
    log.addHandler(fileHandler)
    log.addHandler(streamHandler)

    return log
