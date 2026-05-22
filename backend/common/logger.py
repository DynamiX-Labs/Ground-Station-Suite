# Copyright (c) 2025 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


import logging
import logging.config

import yaml

from .arguments import arguments
from .logconfig import resolve_log_config_path


def get_logger_config(args):
    """
    Loads a logging configuration.

    This function retrieves the logging configuration in YAML format
    from the file path provided in the arguments, converts it to a Python
    dictionary, and returns it. The configuration is useful for setting up
    logging behavior in an application.

    :param args: Parsed arguments containing the file path to the logging configuration.
    :type args: argparse.Namespace
    :return: Python dictionary with logging configuration.
    :rtype: dict
    :raises FileNotFoundError: If the specified logging configuration file cannot be found.
    :raises yaml.YAMLError: If the YAML configuration file cannot be parsed due to invalid syntax.
    """

    resolved_path = resolve_log_config_path(args.log_config)
    args.log_config = str(resolved_path)

    def yaml_to_json_config(filepath):
        with open(filepath, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)

    logging_config = yaml_to_json_config(resolved_path)

    return logging_config


def get_logger(args):
    """
    Obtains a logger instance configured according to the given logging configuration.

    This function reads the logging configuration from a YAML file specified in the provided
    arguments, converts it to a JSON-compatible dictionary, and then applies it to configure
    the Python logging module. It retrieves a logger instance named "ground-station" and logs
    an informational message containing the provided arguments.

    :param args: The command-line arguments containing the path to the logging
                 configuration file (YAML format).
    :type args: argparse.Namespace
    :return: A logger instance named "ground-station".
    :rtype: logging.Logger
    """
    logging_config = get_logger_config(args)

    logging.config.dictConfig(logging_config)

    log = logging.getLogger("ground-station")
    log.setLevel(args.log_level)

    return log


# setup a logger
logger = get_logger(arguments)
