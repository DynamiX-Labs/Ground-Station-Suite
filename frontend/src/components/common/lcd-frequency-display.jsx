import React from 'react';
import { Box, Typography } from '@mui/material';
import { styled } from '@mui/material/styles';

const LCDContainer = styled(Box)(({ theme, variant = 'green' }) => {
    const colors = {
        green: {
            bg: 'linear-gradient(145deg, #0a0f0a, #0d1a0d)',
            border: '#1a3d1a',
            text: '#00ff00',
            glow: '#00ff00'
        },
        amber: {
            bg: 'linear-gradient(145deg, #0f0f0a, #1a1a0d)',
            border: '#3d3d1a',
            text: '#ffcc00',
            glow: '#ffcc00'
        },
        red: {
            bg: 'linear-gradient(145deg, #0f0a0a, #1a0d0d)',
            border: '#3d1a1a',
            text: '#ff3333',
            glow: '#ff3333'
        }
    };

    const color = colors[variant];

    return {
        pt: '4px',
        display: 'block',
        background: color.bg,
        border: `1px solid ${color.border}`,
        borderRadius: '3px',
        padding: '3px 6px',
        boxShadow: `inset 0 0 8px rgba(0, 0, 0, 0.4)`,
        position: 'relative',
        overflow: 'hidden',
        minWidth: 'fit-content',

        '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: `repeating-linear-gradient(
        0deg,
        transparent,
        transparent 1px,
        ${color.text}05 1px,
        ${color.text}05 2px
      )`,
            pointerEvents: 'none',
            zIndex: 1,
        },

        '& .lcd-content': {
            position: 'relative',
            zIndex: 2,
        }
    };
});

const LCDLabel = styled(Typography)(({ theme, variant = 'green' }) => {
    const colors = {
        green: { text: '#00ff00', glow: '#00ff00', shadow: '#003300' },
        amber: { text: '#ffcc00', glow: '#ffcc00', shadow: '#332200' },
        red: { text: '#ff3333', glow: '#ff3333', shadow: '#330000' }
    };

    const color = colors[variant];

    return {
        fontFamily: '"Courier New", "Lucida Console", monospace',
        fontSize: '0.7rem',
        color: color.text,
        textShadow: `
      0 0 2px ${color.glow},
      0 1px 1px ${color.shadow}
    `,
        textAlign: 'center',
        opacity: 0.9,
        marginBottom: '2px',
        lineHeight: 1,
    };
});

const LCDDigits = styled(Box)(({ theme, variant = 'green' }) => {
    const colors = {
        green: { text: '#1dd11d', glow: 'rgba(10,128,10,0.63)', shadow: '#003300' },
        amber: { text: '#ffcc00', glow: '#ffcc00', shadow: '#332200' },
        red: { text: '#ff3333', glow: '#ff3333', shadow: '#330000' }
    };

    const color = colors[variant];

    return {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '1px',
        fontFamily: '"Courier New", "Lucida Console", monospace',
        fontSize: '1.1rem',
        fontWeight: 'bold',
        color: color.text,
        textShadow: `
      0 0 4px ${color.glow},
      0 0 8px ${color.glow},
      0 1px 2px ${color.shadow}
    `,
        letterSpacing: '0.05em',
        lineHeight: 1,

        '& .lcd-digit': {
            paddingTop: '3px',
            display: 'inline-block',
            width: '0.8em',
            textAlign: 'center',
            background: `rgba(0, 0, 0, 0.3)`,
            borderRadius: '1px',
            position: 'relative',
            borderLeft: `1px solid ${color.text}20`,
            borderRight: `1px solid ${color.text}20`,

            '&::before': {
                content: '"8"',
                position: 'absolute',
                top: 4,
                left: 0,
                right: 0,
                bottom: 0,
                color: `${color.text}08`,
                zIndex: -1,
            }
        },

        '& .lcd-digit-empty': {
            paddingTop: '3px',
            display: 'inline-block',
            width: '0.8em',
            textAlign: 'center',
            background: `rgba(0, 0, 0, 0.3)`,
            borderRadius: '1px',
            position: 'relative',
            borderLeft: `1px solid ${color.text}20`,
            borderRight: `1px solid ${color.text}20`,
            opacity: 0.3,

            '&::before': {
                content: '"8"',
                position: 'absolute',
                top: 4,
                left: 0,
                right: 0,
                bottom: 0,
                color: `${color.text}08`,
                zIndex: -1,
            }
        },

        '& .lcd-separator': {
            margin: '0 -4px -14px -3px',
            fontSize: '0.8em',
            opacity: 0.7,
        }
    };
});

const LCDUnit = styled(Typography)(({ theme, variant = 'green' }) => {
    const colors = {
        green: { text: '#00ff00', glow: '#00ff00', shadow: '#003300' },
        amber: { text: '#ffcc00', glow: '#ffcc00', shadow: '#332200' },
        red: { text: '#ff3333', glow: '#ff3333', shadow: '#330000' }
    };

    const color = colors[variant];

    return {
        fontFamily: '"Courier New", "Lucida Console", monospace',
        fontSize: '0.6rem',
        color: color.text,
        textShadow: `
      0 0 2px ${color.glow},
      0 1px 1px ${color.shadow}
    `,
        textAlign: 'center',
        opacity: 0.9,
        marginTop: '1px',
        lineHeight: 1,
    };
});

const LCDFrequencyDisplay = ({
                                 frequency,
                                 digits = 8,
                                 showDecimal = true,
                                 unit = 'MHz',
                                 variant = 'green',
                                 size = 'small',
                                 label = '',
                                 fullWidth = true,
                                 frequencyIsOffset = false,
                             }) => {
    // Format frequency to display with proper padding and separators
    const formatFrequencyWithSeparators = (freq, isFullWidth, isOffset) => {
        try {
            if (!freq || freq === 0) {
                if (isFullWidth) {
                    // Return 9 empty digits for full width when frequency is 0 (under 1GHz display)
                    const result = [];
                    for (let i = 0; i < 9; i++) {
                        result.push({ type: 'digit', value: '0', key: i, isEmpty: true });
                        // Add separators at positions 3, 6 from the right
                        if ((9 - i - 1) % 3 === 0 && i < 8) {
                            result.push({ type: 'separator', value: '·', key: `sep-${i}` });
                        }
                    }
                    return result;
                }
                return [{ type: 'digit', value: '0', key: 0 }];
            }

            // If frequency is a float, truncate to integer part only
            let processedFreq = freq;
            if (typeof freq === 'number' && freq % 1 !== 0) {
                processedFreq = Math.trunc(freq);
            }

            // Convert to string and handle negative numbers
            const freqStr = processedFreq.toString();
            const isNegative = freqStr.startsWith('-');
            const absFreqStr = isNegative ? freqStr.slice(1) : freqStr;

            // Remove decimal point for processing (shouldn't be needed now, but keeping for safety)
            const cleanFreqStr = absFreqStr.replace('.', '');

            let finalFreqStr = cleanFreqStr;

            // Determine if frequency is under 1GHz (1,000,000,000 Hz)
            const isUnder1GHz = processedFreq < 1000000000;
            const totalDigits = isUnder1GHz ? 9 : 11;

            // Handle fullWidth mode
            if (isFullWidth) {
                if (!isOffset) {
                    // For regular frequencies, pad to 8 or 11 digits based on size
                    finalFreqStr = cleanFreqStr.padStart(totalDigits, '0');
                }
                // For offset frequencies, keep finalFreqStr as is (no padding)
            }

            // Add separators every 3 digits from the right
            const result = [];

            // If fullWidth, create the full digit structure
            if (isFullWidth) {
                if (isOffset) {
                    // For offset frequencies: show empty digits on the left, actual digits on the right
                    const actualDigits = cleanFreqStr.length;
                    const signSpace = isOffset ? 1 : 0; // Always reserve space for sign when isOffset
                    const emptyDigits = totalDigits - actualDigits - signSpace;

                    // Add empty digits first
                    for (let i = 0; i < emptyDigits; i++) {
                        const positionFromRight = totalDigits - i - 1;
                        result.push({ type: 'digit', value: '0', key: i, isEmpty: true });

                        // Add separator after every 3 digits (except for the last digit)
                        if (positionFromRight > 0 && positionFromRight % 3 === 0) {
                            result.push({ type: 'separator', value: '·', key: `sep-${i}` });
                        }
                    }

                    // Add sign right before the actual digits (always show + or - for offset)
                    if (isOffset) {
                        result.push({ type: 'digit', value: isNegative ? '-' : '+', key: 'sign' });
                    }

                    // Add actual digits
                    for (let i = 0; i < actualDigits; i++) {
                        const digit = cleanFreqStr[i];
                        const positionFromRight = actualDigits - i - 1;
                        const actualIndex = emptyDigits + signSpace + i;

                        result.push({ type: 'digit', value: digit, key: actualIndex });

                        // Add separator after every 3 digits (except for the last digit)
                        if (positionFromRight > 0 && positionFromRight % 3 === 0) {
                            result.push({ type: 'separator', value: '·', key: `sep-${actualIndex}` });
                        }
                    }
                } else {
                    // Add negative sign at the beginning for regular frequencies
                    if (isNegative) {
                        result.push({ type: 'digit', value: '-', key: 'neg' });
                    }

                    // For regular frequencies, create digit positions with padding (8 or 11 based on frequency)
                    for (let i = 0; i < totalDigits; i++) {
                        const digit = finalFreqStr[i] || '0';
                        const positionFromRight = totalDigits - i - 1;
                        const isEmpty = finalFreqStr[i] === '0' && i < (totalDigits - cleanFreqStr.length);

                        result.push({ type: 'digit', value: digit, key: i, isEmpty });

                        // Add a separator after every 3 digits (except for the last digit)
                        if (positionFromRight > 0 && positionFromRight % 3 === 0) {
                            result.push({ type: 'separator', value: '·', key: `sep-${i}` });
                        }
                    }
                }
            } else {
                // For non-fullWidth: show sign when it's an offset or when it's negative
                if (isOffset || isNegative) {
                    result.push({ type: 'digit', value: isNegative ? '-' : '+', key: 'sign' });
                }

                // Regular processing for non-fullWidth frequencies
                for (let i = 0; i < finalFreqStr.length; i++) {
                    const digit = finalFreqStr[i];
                    const positionFromRight = finalFreqStr.length - i - 1;

                    result.push({ type: 'digit', value: digit, key: i });

                    // Add a separator after every 3 digits (except for the last digit)
                    if (positionFromRight > 0 && positionFromRight % 3 === 0) {
                        result.push({ type: 'separator', value: '·', key: `sep-${i}` });
                    }
                }
            }

            return result;
        } catch (error) {
            console.error('Error formatting frequency:', error);
            // Fallback to simple zero
            return [{ type: 'digit', value: '0', key: 0 }];
        }
    };

    const formattedElements = formatFrequencyWithSeparators(frequency, fullWidth, frequencyIsOffset);
    const fontSize = size === 'large' ? '1.4rem' : size === 'medium' ? '1.2rem' : '1.1rem';

    // Ensure formattedElements is always an array
    const elementsArray = Array.isArray(formattedElements) ? formattedElements : [];

    return (
        <LCDContainer variant={variant}>
            <Box className="lcd-content">
                {label && (
                    <LCDLabel variant={variant}>
                        {label}
                    </LCDLabel>
                )}
                <LCDDigits variant={variant} sx={{ fontSize }}>
                    {elementsArray.map((element) => (
                        element.type === 'digit' ? (
                            <span key={element.key} className={element.isEmpty ? "lcd-digit-empty" : "lcd-digit"}>
                                {element.value}
                            </span>
                        ) : (
                            <span key={element.key} className="lcd-separator">
                                {element.value}
                            </span>
                        )
                    ))}
                    {/*{showDecimal && (*/}
                    {/*    <span className="lcd-decimal">.</span>*/}
                    {/*)}*/}
                </LCDDigits>
                {/*{unit && (*/}
                {/*    <LCDUnit variant={variant}>*/}
                {/*        {unit}*/}
                {/*    </LCDUnit>*/}
                {/*)}*/}
            </Box>
        </LCDContainer>
    );
};

export default LCDFrequencyDisplay;