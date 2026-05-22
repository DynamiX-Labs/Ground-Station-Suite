import React, {useState} from "react";


const ProgressFormatter = React.memo(function ProgressFormatter({params, row: rowProp, nowMs}) {
    const [progressBarHeight, setProgressBarHeight] = useState(14);
    const row = rowProp ?? params?.row;
    const now = nowMs != null ? new Date(nowMs) : new Date();
    const startDate = new Date(row.event_start);
    const endDate = new Date(row.event_end);

    if (row.is_geostationary || row.is_geosynchronous) {
        return "∞";
    }

    // Calculate peak time based on available data
    // Assuming peak_time is available in the data, or we can calculate it from event_start and event_end
    // If peak_time isn't available, we can estimate it as the midpoint
    const peakTime = row.peak_time ? new Date(row.peak_time) :
        new Date(startDate.getTime() + (endDate.getTime() - startDate.getTime()) / 2);

    // Calculate positions as percentages of the total timeline
    const totalDuration = endDate - startDate;
    const peakPosition = ((peakTime - startDate) / totalDuration) * 100;
    const color1 = '#ef5350';
    const color2 = '#ffa726';
    const color3 = '#66bb6a';
    const color4 = '#ffa726';
    const color5 = '#ef5350';
    const passGradient = `linear-gradient(to right, ${color1}, ${color2}, ${color3} ${peakPosition}%, ${color4}, ${color5})`;

    // If the pass hasn't started yet
    if (startDate > now) {
        return (
            <div style={{width: '100%', position: 'relative', height: '35px'}}>
                {/* Timeline bar */}
                <div style={{
                    height: `${progressBarHeight}px`,
                    backgroundColor: 'white',
                    width: '100%',
                    borderRadius: '4px',
                    position: 'absolute',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    border: '1px solid white'
                }}/>

                {/* Progress percentage (0% for not started) */}
                <div style={{
                    position: 'absolute',
                    right: '2px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    fontSize: '12px',
                    color: 'rgba(0, 0, 0, 1)',
                    fontWeight: 'bold',
                    zIndex: 5
                }}>
                    0%
                </div>
            </div>
        );
    }

    // If the pass has ended
    if (endDate < now) {
        return (
            <div style={{width: '100%', position: 'relative', height: '35px'}}>
                {/* Timeline bar - completed */}
                <div style={{
                    height: `${progressBarHeight}px`,
                    background: passGradient,
                    width: '100%',
                    borderRadius: '4px',
                    position: 'absolute',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    border: '1px solid white'
                }}/>

                {/* Progress percentage (100% for completed) */}
                <div style={{
                    position: 'absolute',
                    right: '2px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    fontSize: '12px',
                    color: 'white',
                    fontWeight: 'bold',
                    zIndex: 5,
                    textShadow: '0 0 2px black'
                }}>
                    100%
                </div>
            </div>
        );
    }

    // If the pass is in progress
    const elapsedDuration = now - startDate;
    const progressPercentage = Math.round((elapsedDuration / totalDuration) * 100);

    return (
        <div style={{width: '100%', position: 'relative', height: '35px'}}>
            {/* Timeline background */}
            <div style={{
                height: `${progressBarHeight}px`,
                backgroundColor: 'white',
                width: '100%',
                borderRadius: '4px',
                position: 'absolute',
                top: '50%',
                transform: 'translateY(-50%)',
                border: '1px solid white'
            }}/>

            {/* Progress filled part */}
            <div style={{
                height: `${progressBarHeight}px`,
                background: passGradient,
                width: '100%',
                borderRadius: '4px',
                position: 'absolute',
                top: '50%',
                transform: 'translateY(-50%)',
                zIndex: 1,
                clipPath: `polygon(0 0, ${progressPercentage}% 0, ${progressPercentage}% 100%, 0 100%)`,
                border: '1px solid white'
            }}/>

            {/* Current position indicator */}
            <div style={{
                height: `${progressBarHeight * 1.5}px`,
                width: `${progressBarHeight * 1.5}px`,
                backgroundColor: '#1976d2',
                borderRadius: '50%',
                position: 'absolute',
                left: `calc(${progressPercentage}% - ${progressBarHeight}px)`,
                top: '50%',
                transform: 'translateY(-50%)',
                zIndex: 4,
                border: '1px solid white',
                display: 'none',
            }} title={`Current progress: ${progressPercentage}%`}/>

            {/* Progress percentage (current %) */}
            <div style={{
                position: 'absolute',
                right: '2px',
                top: '50%',
                transform: 'translateY(-50%)',
                fontSize: '12px',
                color: 'rgba(0, 0, 0, 1)',
                fontWeight: 'bold',
                zIndex: 5
            }}>
                {progressPercentage}%
            </div>

            {/* Clipped container for foreground text */}
            <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                clipPath: `polygon(0 0, ${progressPercentage}% 0, ${progressPercentage}% 100%, 0 100%)`,
            }}>
                <div style={{
                    position: 'absolute',
                    right: '2px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    fontSize: '12px',
                    color: 'white',
                    fontWeight: 'bold',
                    zIndex: 6,
                    textShadow: '0 0 2px black'
                }}>
                    {progressPercentage}%
                </div>
            </div>
        </div>
    );
});

export default ProgressFormatter;
