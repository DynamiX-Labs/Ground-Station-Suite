import { getColorForPower } from './worker-modules/color-maps.js';

export function createDomTileWaterfallRenderer({
    canvasA,
    canvasB,
    width,
    height,
    colorMap,
    dbRange,
    backgroundColor = '#000000',
    onMetrics,
}) {
    if (!canvasA || !canvasB || !width || !height) {
        return null;
    }

    const state = {
        canvasA,
        canvasB,
        ctxA: canvasA.getContext('2d', { alpha: true, desynchronized: true, willReadFrequently: false }),
        ctxB: canvasB.getContext('2d', { alpha: true, desynchronized: true, willReadFrequently: false }),
        width,
        height,
        colorMap,
        dbRange,
        backgroundColor,
        palette: null,
        paletteDirty: true,
        imageData: null,
        offsets: [-height, 0],
        activeIndex: 0,
        writeY: height - 1,
        running: true,
        rafId: null,
        timeoutId: null,
        latestFrame: null,
        fftUpdateCount: 0,
        binsUpdateCount: 0,
        renderCount: 0,
        metricsStartTime: performance.now(),
        lastMetricsTime: performance.now(),
    };

    if (!state.ctxA || !state.ctxB) {
        return null;
    }

    function rebuildPalette() {
        const [min, max] = state.dbRange;
        const range = max - min;
        const safeRange = range > 1e-6 ? range : 1;
        const lut = new Uint8Array(256 * 3);

        for (let i = 0; i < 256; i++) {
            const amp = min + (i / 255) * safeRange;
            const c = getColorForPower(amp, state.colorMap, state.dbRange);
            const o = i * 3;
            lut[o] = Math.min(255, Math.max(0, c.r | 0));
            lut[o + 1] = Math.min(255, Math.max(0, c.g | 0));
            lut[o + 2] = Math.min(255, Math.max(0, c.b | 0));
        }

        state.palette = lut;
        state.paletteDirty = false;
    }

    function applyPositions() {
        state.canvasA.style.transform = `translate3d(0, ${state.offsets[0]}px, 0)`;
        state.canvasB.style.transform = `translate3d(0, ${state.offsets[1]}px, 0)`;
    }

    function initializeCanvases() {
        state.canvasA.width = state.width;
        state.canvasA.height = state.height;
        state.canvasB.width = state.width;
        state.canvasB.height = state.height;

        state.canvasA.style.width = '100%';
        state.canvasA.style.height = `${state.height}px`;
        state.canvasB.style.width = '100%';
        state.canvasB.style.height = `${state.height}px`;

        state.ctxA.imageSmoothingEnabled = false;
        state.ctxB.imageSmoothingEnabled = false;
        state.ctxA.fillStyle = state.backgroundColor;
        state.ctxB.fillStyle = state.backgroundColor;
        state.ctxA.fillRect(0, 0, state.width, state.height);
        state.ctxB.fillRect(0, 0, state.width, state.height);

        state.imageData = state.ctxA.createImageData(state.width, 1);
        state.offsets = [-state.height, 0];
        state.activeIndex = 0;
        state.writeY = state.height - 1;
        state.paletteDirty = true;
        applyPositions();
    }

    function scheduleNextTick() {
        if (!state.running) return;
        if (typeof window.requestAnimationFrame === 'function') {
            state.rafId = window.requestAnimationFrame(tick);
            return;
        }
        state.timeoutId = setTimeout(tick, 16);
    }

    function reportMetrics(now) {
        const elapsedMs = now - state.metricsStartTime;
        if (elapsedMs < 1000) return;
        const elapsedSeconds = elapsedMs / 1000;

        if (typeof onMetrics === 'function') {
            onMetrics({
                fftUpdatesPerSecond: Number((state.fftUpdateCount / elapsedSeconds).toFixed(1)),
                binsPerSecond: state.binsUpdateCount / elapsedSeconds,
                renderWaterfallPerSecond: Number((state.renderCount / elapsedSeconds).toFixed(1)),
                totalUpdates: state.fftUpdateCount,
                timeElapsed: elapsedSeconds,
            });
        }

        state.fftUpdateCount = 0;
        state.binsUpdateCount = 0;
        state.renderCount = 0;
        state.metricsStartTime = now;
        state.lastMetricsTime = now;
    }

    function tick(now) {
        if (!state.running) return;

        if (state.latestFrame) {
            const frame = state.latestFrame;
            state.latestFrame = null;
            renderRow(frame);

            const ctx = getActiveContext();
            ctx.putImageData(state.imageData, 0, state.writeY--);

            state.offsets[0] += 1;
            state.offsets[1] += 1;
            applyPositions();

            if (state.writeY < 0) {
                const nextIndex = state.activeIndex === 0 ? 1 : 0;
                state.offsets[nextIndex] -= state.height * 2;
                state.activeIndex = nextIndex;
                state.writeY = state.height - 1;
                applyPositions();
            }

            state.renderCount++;
        }

        reportMetrics(typeof now === 'number' ? now : performance.now());
        scheduleNextTick();
    }

    function getActiveContext() {
        return state.activeIndex === 0 ? state.ctxA : state.ctxB;
    }

    function renderRow(fftData) {
        if (!state.imageData) {
            return;
        }

        if (state.paletteDirty || !state.palette) {
            rebuildPalette();
        }

        const [min, max] = state.dbRange;
        const range = max - min;
        const safeRange = range > 1e-6 ? range : 1;
        const data = state.imageData.data;

        if (fftData.length >= state.width) {
            const skipFactor = fftData.length / state.width;
            for (let x = 0; x < state.width; x++) {
                const fftIndex = Math.min(Math.floor(x * skipFactor), fftData.length - 1);
                const amplitude = fftData[fftIndex];
                let idx = ((amplitude - min) * 255 / safeRange) | 0;
                if (idx < 0) idx = 0;
                if (idx > 255) idx = 255;
                const po = idx * 3;
                const pixelIndex = x * 4;
                data[pixelIndex] = state.palette[po];
                data[pixelIndex + 1] = state.palette[po + 1];
                data[pixelIndex + 2] = state.palette[po + 2];
                data[pixelIndex + 3] = 255;
            }
        } else if (fftData.length > 0) {
            const stretchFactor = state.width / fftData.length;
            for (let i = 0; i < fftData.length; i++) {
                const amplitude = fftData[i];
                let idx = ((amplitude - min) * 255 / safeRange) | 0;
                if (idx < 0) idx = 0;
                if (idx > 255) idx = 255;
                const po = idx * 3;
                const startX = Math.floor(i * stretchFactor);
                const endX = Math.floor((i + 1) * stretchFactor);

                for (let x = startX; x < endX && x < state.width; x++) {
                    const pixelIndex = x * 4;
                    data[pixelIndex] = state.palette[po];
                    data[pixelIndex + 1] = state.palette[po + 1];
                    data[pixelIndex + 2] = state.palette[po + 2];
                    data[pixelIndex + 3] = 255;
                }
            }
        }
    }

    function pushFrame(fftData) {
        if (!fftData || fftData.length === 0) {
            return;
        }
        state.latestFrame = fftData;
        state.fftUpdateCount++;
        state.binsUpdateCount += fftData.length;
    }

    function setConfig({ colorMap, dbRange, backgroundColor }) {
        let requiresReset = false;

        if (colorMap && colorMap !== state.colorMap) {
            state.colorMap = colorMap;
            state.paletteDirty = true;
        }

        if (dbRange && (dbRange[0] !== state.dbRange[0] || dbRange[1] !== state.dbRange[1])) {
            state.dbRange = dbRange;
            state.paletteDirty = true;
        }

        if (backgroundColor && backgroundColor !== state.backgroundColor) {
            state.backgroundColor = backgroundColor;
            requiresReset = true;
        }

        if (requiresReset) {
            initializeCanvases();
        }
    }

    function destroy() {
        state.running = false;
        if (state.rafId !== null && typeof window.cancelAnimationFrame === 'function') {
            window.cancelAnimationFrame(state.rafId);
        }
        if (state.timeoutId !== null) {
            clearTimeout(state.timeoutId);
        }
        state.ctxA = null;
        state.ctxB = null;
        state.imageData = null;
    }

    initializeCanvases();
    scheduleNextTick();

    return {
        pushFrame,
        setConfig,
        destroy,
    };
}
