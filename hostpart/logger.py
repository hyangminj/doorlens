"""
Logger Module
로거 모듈

Provides a configured logger instance for the DoorLens application.
DoorLens 애플리케이션을 위한 설정된 로거 인스턴스를 제공합니다.
"""

import logging
import logging.handlers


def logger(log_path):
    """
    Create and configure a logger instance.
    로거 인스턴스를 생성하고 설정합니다.

    Args:
        log_path (str): Path to the log file where logs will be written
                       로그가 기록될 파일 경로

    Returns:
        logging.Logger: Configured logger instance that writes to both file and console
                       파일과 콘솔 모두에 기록하는 설정된 로거 인스턴스
    """
    # Create logger with unique name
    # 고유한 이름으로 로거 생성
    log = logging.getLogger('snowdeer_log')
    log.setLevel(logging.DEBUG)

    # Define log format: [LEVEL] (filename:line) > message
    # 로그 형식 정의: [레벨] (파일명:줄) > 메시지
    formatter = logging.Formatter('[%(levelname)s] (%(filename)s:%(lineno)d) > %(message)s')

    # File handler: writes logs to file
    # 파일 핸들러: 로그를 파일에 기록
    fileHandler = logging.FileHandler(log_path)

    # Stream handler: writes logs to console
    # 스트림 핸들러: 로그를 콘솔에 출력
    streamHandler = logging.StreamHandler()

    # Apply formatter to both handlers
    # 두 핸들러에 포맷터 적용
    fileHandler.setFormatter(formatter)
    streamHandler.setFormatter(formatter)

    # Add handlers to logger
    # 로거에 핸들러 추가
    log.addHandler(fileHandler)
    log.addHandler(streamHandler)

    return log
