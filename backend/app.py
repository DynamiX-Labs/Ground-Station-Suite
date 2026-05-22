import asyncio
import multiprocessing
import os
import signal
import sys
import threading

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import mock_gnuradio  # Register programmatic gnuradio mock

# Reconfigure stdout/stderr to use UTF-8 on Windows to prevent UnicodeEncodeError on banner block characters
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import uvicorn  # noqa: E402

from common.arguments import arguments  # noqa: E402
from common.logger import get_logger_config, logger  # noqa: E402
from handlers.socket import register_socketio_handlers  # noqa: E402
from server.shmmonitor import start_cleanup_thread  # noqa: E402
from server.shutdown import cleanup_everything, signal_handler  # noqa: E402
from server.startup import app, init_db, sio, socket_app  # noqa: E402
from server.version import get_version_base  # noqa: E402
from video.webrtc import register_webrtc_routes  # noqa: E402

try:
    import setproctitle

    HAS_SETPROCTITLE = True
except ImportError:
    HAS_SETPROCTITLE = False


def print_banner():
    """Print ASCII art banner with version."""
    version = get_version_base()
    print(
        f"""
 ██████╗ ██╗   ██╗███╗   ██╗ █████╗ ███╗   ███╗██╗██╗  ██╗      ██╗      █████╗ ██████╗ ███████╗
 ██╔══██╗╚██╗ ██╔╝████╗  ██║██╔══██╗████╗ ████║██║╚██╗██╔╝      ██║     ██╔══██╗██╔══██╗██╔════╝
 ██║  ██║ ╚████╔╝ ██╔██╗ ██║███████║██╔████╔██║██║ ╚███╔╝  █████╗██║     ███████║██████╔╝███████╗
 ██║  ██║  ╚██╔╝  ██║╚██╗██║██╔══██║██║╚██╔╝██║██║ ██╔██╗  ╚════╝██║     ██╔══██║██╔══██╗╚════██║
 ██████╔╝   ██║   ██║ ╚████║██║  ██║██║ ╚═╝ ██║██║██╔╝ ██╗      ███████╗██║  ██║██████╔╝███████║
 ╚═════╝    ╚═╝   ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═╝      ╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝

                            v{version}
    """
    )


# Set process and thread names
def configure_process_names():
    if HAS_SETPROCTITLE:
        setproctitle.setproctitle("DynamiX-Labs - Main Thread")
    multiprocessing.current_process().name = "DynamiX-Labs - Main"
    threading.current_thread().name = "DynamiX-Labs - Main Thread"


def main() -> None:
    print_banner()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    configure_process_names()

    # Start shared memory monitor thread (for GNU Radio segment tracking)
    logger.info("Starting shared memory monitor thread...")
    start_cleanup_thread(monitor_interval=30)

    # Register other routes
    register_webrtc_routes(app)
    register_socketio_handlers(sio)

    logger.info("Configuring database connection...")
    if arguments.temp_db:
        logger.info(f"Temporary database enabled, using {arguments.db}")
    # Use asyncio.run to create/manage a temporary event loop (Python 3.12+ friendly)
    asyncio.run(init_db())

    # Note: Static files and API routes are already configured in startup.py

    logger.info(f"Starting Ground Station server with parameters {arguments}")
    try:
        uvicorn.run(
            socket_app,
            host=arguments.host,
            port=arguments.port,
            log_config=get_logger_config(arguments),
        )
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt in main")
        cleanup_everything()
        os._exit(0)
    except Exception as e:  # pragma: no cover - startup errors
        logger.error(f"Error starting Ground Station server: {str(e)}")
        logger.exception(e)
        cleanup_everything()
        os._exit(1)


if __name__ == "__main__":
    main()
