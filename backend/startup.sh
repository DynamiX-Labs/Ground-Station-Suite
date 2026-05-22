#!/bin/bash
# Startup script for Ground Station with conditional UHD device support

# Run once here to make sure all new libraries are loaded
ldconfig

# Start system services
echo "Starting D-Bus system daemon..."
mkdir -p /var/run/dbus
rm -f /var/run/dbus/pid
dbus-daemon --system --nofork --nopidfile &
DBUS_PID=$!
sleep 2

# Verify D-Bus is running
if ! ps -p $DBUS_PID > /dev/null; then
    echo "ERROR: D-Bus failed to start"
fi

echo "Starting Avahi mDNS daemon..."
mkdir -p /var/run/avahi-daemon
rm -f /var/run/avahi-daemon/pid
avahi-daemon --no-chroot -D
sleep 3

# Verify Avahi is running
if ! pgrep -x avahi-daemon > /dev/null; then
    echo "ERROR: Avahi daemon failed to start"
    echo "Attempting to start with debug mode..."
    avahi-daemon --no-chroot -D --debug
else
    echo "Avahi daemon started successfully"
fi

# Start SDRplay API service
/opt/sdrplay_api/sdrplay_apiService &
sleep 2

# Configure GNU Radio buffer type (defaults to vmcirc_mmap_tmpfile to prevent shmget exhaustion)
export GR_BUFFER_TYPE=${GR_BUFFER_TYPE:-vmcirc_mmap_tmpfile}
echo "Using GNU Radio buffer type: $GR_BUFFER_TYPE"

# Create GNU Radio config to use mmap-based buffers
mkdir -p /root/.gnuradio
cat > /root/.gnuradio/config.conf << 'EOF'
[vmcircbuf]
default_factory = gr_vmcircbuf_mmap_tmpfile_factory
EOF
echo "Configured GNU Radio to use mmap-based circular buffers"

# Set UHD images directory (defaults to /app/backend/data/uhd_images if not set)
export UHD_IMAGES_DIR=${UHD_IMAGES_DIR:-/app/backend/data/uhd_images}
echo "Using UHD images directory: $UHD_IMAGES_DIR"

# Set UHD config directory (defaults to /app/backend/data/uhd_config if not set)
export UHD_CONFIG_DIR=${UHD_CONFIG_DIR:-/app/backend/data/uhd_config}
echo "Using UHD config directory: $UHD_CONFIG_DIR"

# Create directories if they don't exist
mkdir -p "$UHD_IMAGES_DIR"
mkdir -p "$UHD_CONFIG_DIR"

# Create default uhd.conf if it doesn't exist
if [ ! -f "$UHD_CONFIG_DIR/uhd.conf" ]; then
    cat > "$UHD_CONFIG_DIR/uhd.conf" << 'EOF'
# UHD Configuration File
# Map device serial numbers to specific FPGA images
#
# Format:
# [type=b200,serial=XXXXXXXX]
# fpga=/app/backend/data/uhd_images/custom_fpga.bin
#
# You can add multiple device configurations below:

EOF
    echo "Created default uhd.conf at $UHD_CONFIG_DIR/uhd.conf"
fi

# Download official UHD images to the configured directory
/usr/local/bin/uhd_images_downloader

# Copy LibreSDR FPGA image from build location to persistent storage
if [ -f /usr/local/share/uhd/images/libresdr_b210.bin ]; then
    # Copy with original name
    cp /usr/local/share/uhd/images/libresdr_b210.bin "$UHD_IMAGES_DIR/libresdr_b210.bin"
    echo "LibreSDR FPGA image installed to $UHD_IMAGES_DIR"
else
    echo "Warning: LibreSDR FPGA image not found at /usr/local/share/uhd/images/libresdr_b210.bin"
fi



# Show a list of UHD images
echo "UHD FPGA images in $UHD_IMAGES_DIR:"
ls -lh "$UHD_IMAGES_DIR"/*.bin 2>/dev/null || echo "No UHD images found yet in $UHD_IMAGES_DIR"

# Start the application
echo "Starting Ground Station application..."
cd /app/backend
exec /app/venv/bin/python app.py --log-level=INFO --host=0.0.0.0 --port=7000
