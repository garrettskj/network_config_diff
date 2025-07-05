import os
import threading
from typing import Any

import logzero
from flask import Flask, jsonify, render_template, request
from logzero import logger

from lib.config_diff import ConfigDiffer
from lib.network_client import NetworkClient

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logzero.loglevel(getattr(logzero, log_level, logzero.INFO))

# Log to file if specified
log_file = os.environ.get("LOG_FILE")
if log_file:
    logzero.logfile(log_file, maxBytes=1e6, backupCount=3)

app = Flask(__name__)
logger.info("Starting Config Diff application")

network_client = NetworkClient()
config_differ = ConfigDiffer()


@app.route("/")
def index() -> str:
    """Main page with dual device input forms."""
    logger.debug("Serving index page")
    return render_template("index.html")


@app.route("/compare", methods=["POST"])
def compare_configs() -> dict[str, Any]:
    """Compare configurations from two devices."""
    logger.info("Starting configuration comparison request")

    # Get input methods for each device
    device1_method = request.form.get("device1_method", "ssh")
    device2_method = request.form.get("device2_method", "ssh")

    logger.info(f"Device 1 method: {device1_method}, Device 2 method: {device2_method}")

    # Handle device 1 configuration
    if device1_method == "ssh":
        device1_ip = request.form.get("device1_ip")
        if not device1_ip:
            return jsonify({
                "error": True,
                "device1_error": "IP address required for SSH connection",
                "device2_error": None
            })

        # Parse IP:port format
        if ":" in device1_ip:
            host, port_str = device1_ip.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                return jsonify({
                    "error": True,
                    "device1_error": "Invalid port number. Use format IP:port (e.g., 192.168.1.1:2222)",
                    "device2_error": None
                })
        else:
            host = device1_ip
            port = 22

        logger.info(f"Device 1: SSH connection to {host}:{port}")
        device1_params = network_client.create_device_params(
            device_type=request.form.get("device1_type", "cisco_ios"),
            host=host,
            username=request.form.get("device1_username", ""),
            password=request.form.get("device1_password", ""),
            timeout=30,
        )
        device1_params["port"] = port
        device1_name = device1_ip
    else:
        # File upload for device 1
        logger.info("Device 1: File upload method")
        device1_file = request.files.get("device1_config")
        if not device1_file or device1_file.filename == "":
            return jsonify({
                "error": True,
                "device1_error": "Configuration file required",
                "device2_error": None
            })

        device1_name = request.form.get("device1_name") or device1_file.filename
        device1_params = None

    # Handle device 2 configuration
    if device2_method == "ssh":
        device2_ip = request.form.get("device2_ip")
        if not device2_ip:
            return jsonify({
                "error": True,
                "device1_error": None,
                "device2_error": "IP address required for SSH connection"
            })

        # Parse IP:port format
        if ":" in device2_ip:
            host, port_str = device2_ip.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                return jsonify({
                    "error": True,
                    "device1_error": None,
                    "device2_error": "Invalid port number. Use format IP:port (e.g., 192.168.1.1:2222)"
                })
        else:
            host = device2_ip
            port = 22

        logger.info(f"Device 2: SSH connection to {host}:{port}")
        device2_params = network_client.create_device_params(
            device_type=request.form.get("device2_type", "cisco_ios"),
            host=host,
            username=request.form.get("device2_username", ""),
            password=request.form.get("device2_password", ""),
            timeout=30,
        )
        device2_params["port"] = port
        device2_name = device2_ip
    else:
        # File upload for device 2
        logger.info("Device 2: File upload method")
        device2_file = request.files.get("device2_config")
        if not device2_file or device2_file.filename == "":
            return jsonify({"error": True, "device1_error": None, "device2_error": "Configuration file required"})

        device2_name = request.form.get("device2_name") or device2_file.filename
        device2_params = None

    results: dict[str, dict[str, str | None]] = {}

    def get_config1() -> None:
        logger.debug("Thread 1: Starting device1 configuration retrieval")
        if device1_method == "ssh":
            config, error = network_client.get_device_config(device1_params)
        else:
            # Read and validate file content
            try:
                config = device1_file.read().decode('utf-8')

                # Validate configuration content
                if not network_client.validate_config_content(config):
                    config = None
                    error = "File does not appear to contain valid network configuration"
                    logger.warning(f"Device 1: Configuration validation failed for {device1_file.filename}")
                else:
                    # Store uploaded configuration
                    try:
                        stored_file = network_client.store_uploaded_config(
                            device1_file.filename,
                            config,
                            request.form.get("device1_name")
                        )
                        logger.info(f"Device 1: Configuration stored to {stored_file}")
                        error = None
                    except Exception as e:
                        logger.warning(f"Device 1: Failed to store uploaded config: {str(e)}")
                        # Don't fail the comparison, just log the storage failure
                        error = None

                    logger.info(f"Device 1: Successfully processed file {device1_file.filename} ({len(config)} characters)")

            except UnicodeDecodeError:
                config = None
                error = "File encoding not supported. Please use UTF-8 text files."
                logger.error(f"Device 1: File encoding error for {device1_file.filename}")
            except Exception as e:
                config = None
                error = f"Failed to read file: {str(e)}"
                logger.error(f"Device 1: File read error - {error}")

        results["device1"] = {"config": config, "error": error}
        logger.debug("Thread 1: Device1 configuration retrieval completed")

    def get_config2() -> None:
        logger.debug("Thread 2: Starting device2 configuration retrieval")
        if device2_method == "ssh":
            config, error = network_client.get_device_config(device2_params)
        else:
            # Read and validate file content
            try:
                config = device2_file.read().decode('utf-8')

                # Validate configuration content
                if not network_client.validate_config_content(config):
                    config = None
                    error = "File does not appear to contain valid network configuration"
                    logger.warning(f"Device 2: Configuration validation failed for {device2_file.filename}")
                else:
                    # Store uploaded configuration
                    try:
                        stored_file = network_client.store_uploaded_config(
                            device2_file.filename,
                            config,
                            request.form.get("device2_name")
                        )
                        logger.info(f"Device 2: Configuration stored to {stored_file}")
                        error = None
                    except Exception as e:
                        logger.warning(f"Device 2: Failed to store uploaded config: {str(e)}")
                        # Don't fail the comparison, just log the storage failure
                        error = None

                    logger.info(f"Device 2: Successfully processed file {device2_file.filename} ({len(config)} characters)")

            except UnicodeDecodeError:
                config = None
                error = "File encoding not supported. Please use UTF-8 text files."
                logger.error(f"Device 2: File encoding error for {device2_file.filename}")
            except Exception as e:
                config = None
                error = f"Failed to read file: {str(e)}"
                logger.error(f"Device 2: File read error - {error}")

        results["device2"] = {"config": config, "error": error}
        logger.debug("Thread 2: Device2 configuration retrieval completed")

    logger.info("Starting parallel configuration retrieval")
    thread1 = threading.Thread(target=get_config1, name="Device1-Thread")
    thread2 = threading.Thread(target=get_config2, name="Device2-Thread")

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()
    logger.info("Parallel configuration retrieval completed")

    if results["device1"]["error"] or results["device2"]["error"]:
        logger.warning(f"Configuration retrieval errors - Device1: {results['device1']['error']}, Device2: {results['device2']['error']}")
        return jsonify(
            {
                "error": True,
                "device1_error": results["device1"]["error"],
                "device2_error": results["device2"]["error"],
            }
        )

    logger.info("Both configurations retrieved successfully, generating diff")

    diff_html = config_differ.generate_side_by_side_diff(
        results["device1"]["config"],
        results["device2"]["config"],
        device1_name,
        device2_name,
    )

    # Get diff statistics
    diff_stats = config_differ.get_diff_statistics(
        results["device1"]["config"],
        results["device2"]["config"],
    )

    logger.info(f"Configuration comparison completed successfully for {device1_name} and {device2_name}")

    return jsonify(
        {
            "error": False,
            "diff_html": diff_html,
            "device1_name": device1_name,
            "device2_name": device2_name,
            "diff_stats": diff_stats,
        }
    )


@app.route("/diff")
def diff_view() -> str:
    """Diff view template."""
    logger.debug("Serving diff view page")
    return render_template("diff.html")


if __name__ == "__main__":
    # Check environment to determine if we're in development or production
    flask_env = os.environ.get("FLASK_ENV", "production")
    debug_mode = flask_env == "development"
    
    if debug_mode:
        logger.info("Starting Flask development server with debug mode")
        app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True)
    else:
        logger.info("Starting Flask production server")
        app.run(host="0.0.0.0", port=5000, debug=False)
