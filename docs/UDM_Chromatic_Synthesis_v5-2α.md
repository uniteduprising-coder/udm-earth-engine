# UDM COSMOLOGY ENGINE v5.2α — DAY, NIGHT, TERMINATOR, & CHROMATIC SYNTHESIS

Derived from the v5.2α mathematical ledger, `spectra/luminary_lines.csv`, and Sun/Moon node geometry (33 mi @ 3,000 mi altitude).

**API:** `GET /api/cosmology/chromatic?lat=&lon=` or `?r_mi=&theta_rad=`

## 1 · Day and Night

- **Sun:** 33 mi diameter, 3,000 mi altitude → ~0.63° angular diameter; illuminates a **circular patch** (~3,000–4,000 mi radius), not a hemisphere.
- **Night:** outside the direct illumination cone; baseline **aetheric glow** `I ∝ exp(−r/210 mi)` with 14.2 min pulsation.
- **Moon:** same size/altitude, +11.1° phase; self-luminous/resonant node (spectrum matches Sun).

## 2 · Terminator

- Geometric terminator ~3,000–3,300 mi from subsolar point; twilight zone ~50–100 mi.
- Firmament `n'(z)` extends twilight ~3.75 mi; **aetheric fluorescence** dominates extended dawn/dusk ring.
- **Four-fold modulation** at island longitudes (45°, 135°, 225°, 315°) → rounded-square terminator.
- **14.2 min pulsation** from `ρ_a ∝ cos(4θ − ω_a t)`.

## 3 · Chromatic Predictions

| Phenomenon | UDM v5.2α |
|------------|-----------|
| Daylight | Golden-green (557 nm dominant) |
| Sky | Pale golden-green (not Rayleigh blue) |
| Moonlight | Golden-green |
| Skin undertone | Greenish-golden, minimal UV driver |
| CCT | ~4,500–5,000 K |

## 4 · Implementation

- Module: `src/earth/cosmology/chromatic.py`
- Baked: `public/data/cosmology/chromatic.json`
- Tests: `tests/test_chromatic.py`