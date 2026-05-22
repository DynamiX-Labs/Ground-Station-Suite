const BODY_BASE_URL = '/body-icons';
const MISSION_BASE_URL = '/mission-icons';
const SATELLITE_BASE_URL = '/satimages';

const BODY_ICON_FILE_BY_ID = Object.freeze({
    sun: 'sun-sphere-icon.png',
    mercury: 'mercury-sphere-icon.png',
    venus: 'venus-sphere-icon.png',
    earth: 'earth-sphere-icon.png',
    moon: 'moon-sphere-icon.png',
    mars: 'mars-sphere-icon.png',
    jupiter: 'jupiter-sphere-icon.png',
    io: 'io-sphere-icon.png',
    europa: 'europa-sphere-icon.png',
    ganymede: 'ganymede-sphere-icon.png',
    callisto: 'callisto-sphere-icon.png',
    saturn: 'saturn-sphere-icon.png',
    mimas: 'mimas-sphere-icon.png',
    enceladus: 'enceladus-sphere-icon.png',
    tethys: 'tethys-sphere-icon.png',
    dione: 'dione-sphere-icon.png',
    rhea: 'rhea-sphere-icon.png',
    titan: 'titan-sphere-icon.png',
    iapetus: 'iapetus-sphere-icon.png',
    uranus: 'uranus-sphere-icon.png',
    neptune: 'neptune-sphere-icon.png',
    ceres: 'ceres-sphere-icon.png',
    haumea: 'haumea-sphere-icon.png',
    makemake: 'makemake-sphere-icon.png',
    eris: 'eris-sphere-icon.png',
    'venus-surface': 'venus-surface-sphere-icon.png',
});

const BODY_ALIASES = Object.freeze({
    sol: 'sun',
    luna: 'moon',
    'saturn-vi': 'titan',
    saturnvi: 'titan',
    'naif-606': 'titan',
    '606': 'titan',
});

const MISSION_ICON_FILE_BY_KEY = Object.freeze({
    'voyager-1': 'voyager1-spacecraft-icon.png',
    voyager1: 'voyager1-spacecraft-icon.png',
    'voyager-2': 'voyager2-spacecraft-icon.png',
    voyager2: 'voyager2-spacecraft-icon.png',
    'new-horizons': 'newhorizons-spacecraft-icon.png',
    newhorizons: 'newhorizons-spacecraft-icon.png',
    '-98': 'newhorizons-spacecraft-icon.png',
    'parker-solar-probe': 'parkersolarprobe-spacecraft-icon.png',
    parkersolarprobe: 'parkersolarprobe-spacecraft-icon.png',
    'solar-orbiter': 'solarorbiter-spacecraft-icon.png',
    solarorbiter: 'solarorbiter-spacecraft-icon.png',
    'stereo-a': 'stereoa-spacecraft-icon.png',
    stereoa: 'stereoa-spacecraft-icon.png',
    '-234': 'stereoa-spacecraft-icon.png',
    'stereo-b': 'stereob-spacecraft-icon.png',
    stereob: 'stereob-spacecraft-icon.png',
    '-235': 'stereob-spacecraft-icon.png',
    juno: 'juno-spacecraft-icon.png',
    '-61': 'juno-spacecraft-icon.png',
    cassini: 'cassini-spacecraft-icon.png',
    galileo: 'galileo-spacecraft-icon.png',
    maven: 'maven-spacecraft-icon.png',
    marsodyssey: 'marsodyssey-spacecraft-icon.png',
    'mars-odyssey': 'marsodyssey-spacecraft-icon.png',
    odyssey: 'marsodyssey-spacecraft-icon.png',
    '-53': 'marsodyssey-spacecraft-icon.png',
    mro: 'mro-spacecraft-icon.png',
    'mars-reconnaissance-orbiter': 'mro-spacecraft-icon.png',
    perseverance: 'perseverance-spacecraft-icon.png',
    'mars-2020': 'perseverance-spacecraft-icon.png',
    mars2020: 'perseverance-spacecraft-icon.png',
    bepicolombo: 'bepicolombo-spacecraft-icon.png',
    'bepi-colombo': 'bepicolombo-spacecraft-icon.png',
    hayabusa2: 'hayabusa2-spacecraft-icon.png',
    'hayabusa-2': 'hayabusa2-spacecraft-icon.png',
    exomars: 'exomars-spacecraft-icon.png',
    dawn: 'dawn-spacecraft-icon.png',
    'osiris-rex': 'osirisrex-spacecraft-icon.png',
    osirisrex: 'osirisrex-spacecraft-icon.png',
    '-64': 'osirisrex-spacecraft-icon.png',
    juice: 'juice-spacecraft-icon.png',
    euclid: 'euclid-spacecraft-icon.png',
    dart: 'dart-spacecraft-icon.png',
    lro: 'lunarreconnaissanceorbiter-spacecraft-icon.png',
    'lunar-reconnaissance-orbiter': 'lunarreconnaissanceorbiter-spacecraft-icon.png',
    lunarreconnaissanceorbiter: 'lunarreconnaissanceorbiter-spacecraft-icon.png',
    insight: 'insight-spacecraft-icon.png',
    lucy: 'lucy-spacecraft-icon.png',
    '-49': 'lucy-spacecraft-icon.png',
    psyche: 'psyche-spacecraft-icon.png',
    '-255': 'psyche-spacecraft-icon.png',
    curiosity: 'curiosity-spacecraft-icon.png',
    '-76': 'curiosity-spacecraft-icon.png',
    'msl-curiosity': 'curiosity-spacecraft-icon.png',
    'mars-science-laboratory': 'curiosity-spacecraft-icon.png',
    chandrayaan2orbiter: 'chandrayaan2orbiter-spacecraft-icon.png',
    'chandrayaan-2-orbiter': 'chandrayaan2orbiter-spacecraft-icon.png',
    '-152': 'chandrayaan2orbiter-spacecraft-icon.png',
    'ch2-orbiter': 'chandrayaan2orbiter-spacecraft-icon.png',
    chandrayaan3: 'chandrayaan3-spacecraft-icon.png',
    'chandrayaan-3': 'chandrayaan3-spacecraft-icon.png',
    ch3: 'chandrayaan3-spacecraft-icon.png',
    tianwen1: 'tianwen1-spacecraft-icon.png',
    'tianwen-1': 'tianwen1-spacecraft-icon.png',
    rosetta: 'rosetta-spacecraft-icon.png',
    deepimpact: 'deepimpact-spacecraft-icon.png',
    'deep-impact': 'deepimpact-spacecraft-icon.png',
});

export const resolvePreset = (size) => {
    if (size === 'full') return '256';
    const numericSize = Number(size);
    if (!Number.isFinite(numericSize)) return '64';
    if (numericSize <= 64) return '64';
    if (numericSize <= 128) return '128';
    return '256';
};

const normalizeBodyId = (value) => {
    const key = String(value || '')
        .trim()
        .toLowerCase()
        .replace(/^body:/, '')
        .replace(/[_\s]+/g, '-');
    return BODY_ALIASES[key] || key;
};

const normalizeMissionKey = (value) => String(value || '')
    .trim()
    .toLowerCase()
    .replace(/^mission:/, '')
    .replace(/[_\s]+/g, '-');

const normalizeSatelliteId = (value) => {
    const raw = String(value || '')
        .trim()
        .toLowerCase()
        .replace(/^satellite:/, '')
        .replace(/^norad:/, '');
    const digits = raw.match(/\d+/g);
    return digits ? digits.join('') : '';
};

export const resolveBodyIconPath = (bodyId, size) => {
    const normalized = normalizeBodyId(bodyId);
    const filename = BODY_ICON_FILE_BY_ID[normalized];
    if (!filename) return '';
    return `${BODY_BASE_URL}/${resolvePreset(size)}/${filename}`;
};

export const resolveMissionIconPath = (missionKey, size) => {
    const normalized = normalizeMissionKey(missionKey);
    const filename = MISSION_ICON_FILE_BY_KEY[normalized];
    if (!filename) return '';
    return `${MISSION_BASE_URL}/${resolvePreset(size)}/${filename}`;
};

export const resolveSatelliteIconPath = (satelliteId, size) => {
    const normalized = normalizeSatelliteId(satelliteId);
    if (!normalized) return '';
    return `${SATELLITE_BASE_URL}/${resolvePreset(size)}/${normalized}.png`;
};

export const resolveSatelliteFallbackPath = (satelliteId) => {
    const normalized = normalizeSatelliteId(satelliteId);
    if (!normalized) return '';
    return `${SATELLITE_BASE_URL}/full/${normalized}.png`;
};
