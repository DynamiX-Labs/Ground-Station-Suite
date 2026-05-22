import os
import threading
import time

from common.logger import logger
from db import AsyncSessionLocal

# Import all entity modules to register their handlers
from handlers.entities import (
    appsettings,
    celestial,
    decoderconfig,
    groups,
    hardware,
    locations,
    orbitalsources,
    preferences,
    satellites,
    scheduler,
    sessions,
    systeminfo,
    tracking,
    transmitters,
    vfo,
)
from handlers.entities.databasebackup import (
    backup_table,
    full_backup,
    full_restore,
    list_tables,
    restore_table,
)
from handlers.entities.filebrowser import filebrowser_request_routing
from handlers.entities.sdr import sdr_data_request_routing
from handlers.entities.transmitterimport import (
    import_gr_satellites_transmitters,
    import_satdump_transmitters,
)
from handlers.routing import dispatch_request, handler_registry
from pipeline.orchestration.processmanager import process_manager
from server import runtimestate
from server.shutdown import cleanup_everything
from session.service import session_service
from session.socketregistry import SESSIONS
from session.tracker import session_tracker
from tasks.registry import get_task


def _register_all_handlers():
    """Register all entity handlers with the global registry."""
    appsettings.register_handlers(handler_registry)
    satellites.register_handlers(handler_registry)
    orbitalsources.register_handlers(handler_registry)
    groups.register_handlers(handler_registry)
    hardware.register_handlers(handler_registry)
    locations.register_handlers(handler_registry)
    preferences.register_handlers(handler_registry)
    transmitters.register_handlers(handler_registry)
    tracking.register_handlers(handler_registry)
    vfo.register_handlers(handler_registry)
    systeminfo.register_handlers(handler_registry)
    sessions.register_handlers(handler_registry)
    scheduler.register_handlers(handler_registry)
    decoderconfig.register_handlers(handler_registry)
    celestial.register_handlers(handler_registry)


# Register all handlers at module load time
_register_all_handlers()


def register_socketio_handlers(sio):
    """Register Socket.IO event handlers."""

    @sio.on("connect")
    async def connect(sid, environ, auth=None):
        # Import here to avoid circular dependency
        # Prefer reverse-proxy header if present, else fall back to REMOTE_ADDR
        xff = environ.get("HTTP_X_FORWARDED_FOR") or environ.get("X-Forwarded-For")
        if xff:
            # Take the first IP in the comma-separated list
            client_ip = xff.split(",")[0].strip()
        else:
            client_ip = environ.get("REMOTE_ADDR")

        # Extract additional client metadata from HTTP headers
        user_agent = environ.get("HTTP_USER_AGENT")
        origin = environ.get("HTTP_ORIGIN")
        referer = environ.get("HTTP_REFERER")

        logger.info(f"Client {sid} from {client_ip} connected, auth: {auth}")
        SESSIONS[sid] = environ

        # Persist client metadata into SessionTracker so snapshots can include it
        try:
            session_tracker.set_session_metadata(
                sid,
                ip_address=client_ip,
                user_agent=user_agent,
                origin=origin,
                referer=referer,
                connected_at=time.time(),
            )
        except Exception:
            logger.debug("Failed to set session metadata in tracker", exc_info=True)

        # Send current running tasks to newly connected client
        if runtimestate.background_task_manager:
            running_tasks = runtimestate.background_task_manager.get_running_tasks()
            if running_tasks:
                await sio.emit("background_task:list", {"tasks": running_tasks}, to=sid)

    @sio.on("disconnect")
    async def disconnect(sid, environ):
        logger.info(f'Client {sid} from {SESSIONS[sid]["REMOTE_ADDR"]} disconnected')
        del SESSIONS[sid]
        # Clean up session via SessionService (stops processes and clears tracker including metadata)
        await session_service.cleanup_session(sid)

    @sio.on("sdr_data")
    async def handle_sdr_data_requests(sid, cmd, data=None):
        logger.info(f"Received SDR event from: {sid}, with cmd: {cmd}")
        reply = await sdr_data_request_routing(sio, cmd, data, logger, sid)
        return reply

    @sio.on("data_request")
    async def handle_frontend_data_requests(sid, cmd, data=None):
        logger.debug(f"Received event from: {sid}, with cmd: {cmd}")
        reply = await dispatch_request(sio, cmd, data, logger, sid, handler_registry)
        return reply

    @sio.on("data_submission")
    async def handle_frontend_data_submissions(sid, cmd, data=None):
        logger.debug(f"Received event from: {sid}, with cmd: {cmd}, and data: {data}")
        reply = await dispatch_request(sio, cmd, data, logger, sid, handler_registry)
        return reply

    @sio.on("file_browser")
    async def handle_file_browser_requests(sid, cmd, data=None):
        logger.info(f"Received file browser event from: {sid}, with cmd: {cmd}")
        # No callback - responses are emitted as events
        await filebrowser_request_routing(sio, cmd, data, logger, sid)

    @sio.on("service_control")
    async def handle_service_control_requests(sid, cmd, data=None):
        logger.info(
            f"Received service control event from: {sid}, with cmd: {cmd}, and data: {data}"
        )
        if cmd == "restart_service":
            logger.info(
                f"Service restart requested by client {sid} with IP {SESSIONS[sid]['REMOTE_ADDR']}"
            )

            def delayed_shutdown():
                """Shutdown after a small delay to allow response to be sent."""
                time.sleep(2)
                logger.info("Service restart requested via Socket.IO - initiating shutdown...")
                cleanup_everything()
                logger.info("Forcing container exit for restart...")
                os._exit(0)

            shutdown_thread = threading.Thread(target=delayed_shutdown)
            shutdown_thread.daemon = True
            shutdown_thread.start()

            return {
                "status": "success",
                "message": "Service restart initiated. All processes will be stopped and container will restart in 2 seconds.",
            }
        return {"status": "error", "message": "Unknown service control command"}

    @sio.on("start-monitoring")
    async def handle_start_monitoring(sid):
        """Start performance monitoring when client requests it."""
        logger.info(f"Performance monitoring start requested by client {sid}")
        process_manager.performance_monitor.enable_monitoring()

    @sio.on("stop-monitoring")
    async def handle_stop_monitoring(sid):
        """Stop performance monitoring when client closes dialog."""
        logger.info(f"Performance monitoring stop requested by client {sid}")
        process_manager.performance_monitor.disable_monitoring()

    @sio.on("database_backup")
    async def handle_database_backup(sid, data=None):
        """Handle database backup and restore operations."""
        logger.info(
            f"Database backup event from: {sid}, action: {data.get('action') if data else None}"
        )

        if not data or "action" not in data:
            return {"success": False, "error": "Missing action parameter"}

        action = data["action"]

        try:
            if action == "list_tables":
                return await list_tables()

            elif action == "backup_table":
                table_name = data.get("table")
                if not table_name:
                    return {"success": False, "error": "Missing table parameter"}
                return await backup_table(table_name)

            elif action == "restore_table":
                table_name = data.get("table")
                sql = data.get("sql")
                delete_first = data.get("delete_first", True)

                if not table_name or not sql:
                    return {"success": False, "error": "Missing table or sql parameter"}

                return await restore_table(table_name, sql, delete_first)

            elif action == "full_backup":
                return await full_backup()

            elif action == "full_restore":
                sql = data.get("sql")
                drop_tables = data.get("drop_tables", True)

                if not sql:
                    return {"success": False, "error": "Missing sql parameter"}

                return await full_restore(sql, drop_tables)

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            logger.error(f"Error in database backup handler: {str(e)}")
            return {"success": False, "error": str(e)}

    @sio.on("transmitter_import")
    async def handle_transmitter_import(sid, data=None):
        """Handle transmitter imports from external sources."""

        logger.info(
            f"Transmitter import event from: {sid}, source: {data.get('source') if data else None}"
        )

        if not data or "source" not in data:
            return {"success": False, "error": "Missing source parameter"}

        source = data["source"]
        try:
            async with AsyncSessionLocal() as session:
                if source == "satdump":
                    return await import_satdump_transmitters(session=session)
                if source == "gr-satellites":
                    return await import_gr_satellites_transmitters(session=session)

                return {"success": False, "error": f"Unknown source: {source}"}
        except Exception as e:
            logger.error(f"Error in transmitter import handler: {str(e)}")
            return {"success": False, "error": str(e)}

    @sio.on("background_task:start")
    async def handle_background_task_start(sid, data=None):
        """Handle request to start a background task."""

        logger.info(f"Background task start request from: {sid}, data: {data}")

        if not runtimestate.background_task_manager:
            return {"success": False, "error": "Background task manager not initialized"}

        if not data or "task_name" not in data:
            return {"success": False, "error": "Missing task_name parameter"}

        try:
            task_name = data["task_name"]
            args = tuple(data.get("args", []))  # Convert to tuple
            kwargs = data.get("kwargs", {})
            name = data.get("name")
            task_id = data.get("task_id")

            # Get task function from registry (prevents arbitrary code execution)
            try:
                task_func = get_task(task_name)
            except KeyError:
                return {"success": False, "error": f"Unknown task: {task_name}"}

            # Start the task
            task_id = await runtimestate.background_task_manager.start_task(
                func=task_func, args=args, kwargs=kwargs, name=name, task_id=task_id
            )

            return {"success": True, "task_id": task_id}

        except Exception as e:
            logger.error(f"Error starting background task: {str(e)}")
            return {"success": False, "error": str(e)}

    @sio.on("background_task:stop")
    async def handle_background_task_stop(sid, data=None):
        """Handle request to stop a background task."""
        logger.info(f"Background task stop request from: {sid}, data: {data}")

        if not runtimestate.background_task_manager:
            return {"success": False, "error": "Background task manager not initialized"}

        if not data or "task_id" not in data:
            return {"success": False, "error": "Missing task_id parameter"}

        try:
            task_id = data["task_id"]
            timeout = data.get("timeout", 5.0)

            # Stop the task
            stopped = await runtimestate.background_task_manager.stop_task(task_id, timeout=timeout)

            if stopped:
                return {"success": True, "task_id": task_id}
            else:
                return {"success": False, "error": "Task not found or already finished"}

        except Exception as e:
            logger.error(f"Error stopping background task: {str(e)}")
            return {"success": False, "error": str(e)}

    @sio.on("background_task:get")
    async def handle_background_task_get(sid, data=None):
        """Handle request to get information about a background task."""
        logger.debug(f"Background task get request from: {sid}, data: {data}")

        if not runtimestate.background_task_manager:
            return {"success": False, "error": "Background task manager not initialized"}

        if not data or "task_id" not in data:
            return {"success": False, "error": "Missing task_id parameter"}

        try:
            task_id = data["task_id"]
            task_info = runtimestate.background_task_manager.get_task(task_id)

            if task_info:
                return {"success": True, "task": task_info}
            else:
                return {"success": False, "error": "Task not found"}

        except Exception as e:
            logger.error(f"Error getting background task: {str(e)}")
            return {"success": False, "error": str(e)}

    @sio.on("background_task:list")
    async def handle_background_task_list(sid, data=None):
        """Handle request to list all background tasks."""
        logger.debug(f"Background task list request from: {sid}")

        if not runtimestate.background_task_manager:
            return {"success": False, "error": "Background task manager not initialized"}

        try:
            only_running = data.get("only_running", False) if data else False

            if only_running:
                tasks = runtimestate.background_task_manager.get_running_tasks()
            else:
                tasks = runtimestate.background_task_manager.get_all_tasks()

            return {"success": True, "tasks": tasks}

        except Exception as e:
            logger.error(f"Error listing background tasks: {str(e)}")
            return {"success": False, "error": str(e)}

    return SESSIONS
