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


import socket
import threading


def forward_data(source, destination):
    """Continuously forward data between source and destination."""
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break  # Connection closed
            # Print the intercepted data (you might want to decode or log it differently)
            print("Intercepted:", data)
            destination.sendall(data)
    except Exception as e:
        print("Error during data forwarding:", e)
    finally:
        source.close()
        destination.close()


def handle_client(client_socket, remote_host, remote_port):
    """Handle a new client connection by connecting to the remote host and bridging data."""
    try:
        # Connect to the remote server
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.connect((remote_host, remote_port))
        print(f"Connected to remote {remote_host}:{remote_port}")
    except Exception as e:
        print("Error connecting to remote server:", e)
        client_socket.close()
        return

    # Set up two threads to forward data in both directions
    client_to_remote = threading.Thread(target=forward_data, args=(client_socket, remote_socket))
    remote_to_client = threading.Thread(target=forward_data, args=(remote_socket, client_socket))

    client_to_remote.start()
    remote_to_client.start()

    client_to_remote.join()
    remote_to_client.join()


def start_proxy(local_host, local_port, remote_host, remote_port):
    """Start the TCP proxy."""
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    proxy_socket.bind((local_host, local_port))
    proxy_socket.listen(5)
    print(f"TCP Proxy listening on {local_host}:{local_port}")

    while True:
        client_socket, addr = proxy_socket.accept()
        print(f"Accepted connection from {addr[0]}:{addr[1]}")
        handler = threading.Thread(
            target=handle_client, args=(client_socket, remote_host, remote_port)
        )
        handler.start()


if __name__ == "__main__":
    # Set up your proxy parameters:
    # - Local host and port where the proxy listens.
    # - Remote host and port to which the traffic is forwarded.
    LOCAL_HOST = "127.0.0.1"
    LOCAL_PORT = 4533
    REMOTE_HOST = "192.168.60.97"  # Replace with the remote server's hostname or IP.
    REMOTE_PORT = 4533  # Replace with the remote server's port.

    start_proxy(LOCAL_HOST, LOCAL_PORT, REMOTE_HOST, REMOTE_PORT)
