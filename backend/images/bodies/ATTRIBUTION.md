Source textures used for generated sphere icons:

- Website: https://www.solarsystemscope.com/textures/
- Copyright/License statement on page: CC BY 4.0

Downloaded texture files used:

- `2k_mercury.jpg`
- `2k_venus_atmosphere.jpg`
- `2k_venus_surface.jpg`
- `2k_earth_daymap.jpg`
- `2k_mars.jpg`
- `2k_jupiter.jpg`
- `2k_saturn.jpg`
- `2k_uranus.jpg`
- `2k_neptune.jpg`
- `2k_moon.jpg`
- `2k_sun.jpg` (legacy source; current Sun icon uses the H-alpha source below)
- `2k_ceres_fictional.jpg`
- `2k_eris_fictional.jpg`
- `2k_haumea_fictional.jpg`
- `2k_makemake_fictional.jpg`

Additional moon texture sources used:

- USGS Astrogeology / planetarymaps.usgs.gov
  - `Io_Galileo_SSI_Global_Mosaic_ClrMerge_1km.tif`
  - `Europa_Voyager_GalileoSSI_global_mosaic_500m.tif`
  - `Ganymede_Voyager_GalileoSSI_Global_ClrMosaic_1435m.tif`
  - `Callisto_Voyager_GalileoSSI_global_mosaic_1km.tif`
- NASA/JPL Image catalog (Color Maps of Saturn moons, 2014)
  - `jpegPIA18434.jpg` (Dione)
  - `jpegPIA18435.jpg` (Enceladus)
  - `jpegPIA18436.jpg` (Iapetus)
  - `jpegPIA18437.jpg` (Mimas)
  - `jpegPIA18438.jpg` (Rhea)
  - `jpegPIA18439.jpg` (Tethys)
- User-provided local texture
  - `titan_map_by_mapperpro_dfqh25n-pre.jpg` (Titan)

Generated icons in this folder are derived from these textures via:

- `backend/scripts/render_planet_icon.py`

Sun H-alpha replacement source (current `sun-sphere-icon.png`):

- File: `Sun in Hydrogen-Alpha on 1-21-18 (24956978767).png`
- URL: https://upload.wikimedia.org/wikipedia/commons/6/60/Sun_in_Hydrogen-Alpha_on_1-21-18_%2824956978767%29.png
- License: CC0
- Author: Stephen Rahn
- Processing note: background black keyed to transparency, then exported to `64/128/256` icon sizes.
