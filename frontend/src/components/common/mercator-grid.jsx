/**
 * @license
 * Copyright (c) 2025 Efstratios Goudelis
 * Modifications and extensions Copyright (C) 2026 DynamiX-Labs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 *
 */

import React from 'react';
import { useMap, Polyline } from 'react-leaflet';
import L from 'leaflet';

// Component to add coordinate grid to the map
const CoordinateGrid = ({
                            latInterval = 15,   // Interval between latitude lines (in degrees)
                            lngInterval = 15,   // Interval between longitude lines (in degrees)
                            latColor = '#888',  // Color for latitude lines
                            lngColor = '#888',  // Color for longitude lines
                            weight = 1,         // Line weight
                            opacity = 0.6,      // Line opacity
                            showLabels = true,  // Whether to show coordinate labels
                            zIndex = 300        // z-index for the grid lines
                        }) => {
    const map = useMap();

    // Generate latitude lines (horizontal)
    const latLines = [];
    for (let lat = -90; lat <= 90; lat += latInterval) {
        if (lat === -90 || lat === 90) continue; // Skip the poles

        const points = [];
        // Create points around the entire globe
        for (let lng = -180; lng <= 180; lng++) {
            points.push([lat, lng]);
        }
        latLines.push({
            positions: points,
            options: {
                color: latColor,
                weight: weight,
                opacity: opacity,
                interactive: false,
                dashArray: lat === 0 ? null : '1, 5', // Equator is solid, others dashed
                zIndex: zIndex
            }
        });

        // Add latitude label if enabled
        if (showLabels) {
            const labelPos = L.latLng(lat, 0);
            L.marker(labelPos, {
                icon: L.divIcon({
                    className: 'coordinate-label',
                    html: `${Math.abs(lat)}°${lat >= 0 ? 'N' : 'S'}`,
                    iconSize: [40, 20],
                    iconAnchor: [20, 10]
                }),
                interactive: false,
                zIndexOffset: zIndex
            }).addTo(map);
        }
    }

    // Generate longitude lines (vertical)
    const lngLines = [];
    for (let lng = -180; lng <= 180; lng += lngInterval) {
        if (lng === 180) continue; // Skip the edge

        const points = [];
        // Create vertical lines
        for (let lat = -90; lat <= 90; lat++) {
            points.push([lat, lng]);
        }
        lngLines.push({
            positions: points,
            options: {
                color: lngColor,
                weight: weight,
                opacity: opacity,
                interactive: false,
                dashArray: lng === 0 ? null : '1, 5', // Prime meridian solid, others dashed
                zIndex: zIndex
            }
        });

        // Add longitude label if enabled
        if (showLabels) {
            const labelPos = L.latLng(0, lng);
            L.marker(labelPos, {
                icon: L.divIcon({
                    className: 'coordinate-label',
                    html: `${Math.abs(lng)}°${lng >= 0 ? 'E' : 'W'}`,
                    iconSize: [40, 20],
                    iconAnchor: [20, 10]
                }),
                interactive: false,
                zIndexOffset: zIndex
            }).addTo(map);
        }
    }

    // Add some CSS for labels if needed
    React.useEffect(() => {
        if (showLabels) {
            const style = document.createElement('style');
            style.innerHTML = `
        .coordinate-label {
          background-color: transparent !important;
          border: none !important;
          font-size: 10px;
          color: #666;
          opacity: 0.6;
          text-shadow: 1px 1px 0 #121212, -1px -1px 0 #121212, 1px -1px 0 #121212, -1px 1px 0 #121212;
          text-align: center;
          font-weight: bold;
        }
      `;
            document.head.appendChild(style);

            return () => {
                document.head.removeChild(style);
            };
        }
    }, [showLabels]);

    return (
        <>
            {latLines.map((line, i) => (
                <Polyline key={`lat-${i}`} positions={line.positions} pathOptions={line.options} />
            ))}
            {lngLines.map((line, i) => (
                <Polyline key={`lng-${i}`} positions={line.positions} pathOptions={line.options} />
            ))}
        </>
    );
};

export default CoordinateGrid;