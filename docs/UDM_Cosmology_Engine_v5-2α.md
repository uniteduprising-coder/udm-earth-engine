# UDM COSMOLOGY ENGINE v5.2α — MASTER SPECIFICATION

**Unified Dielectric Model — Polar-Stator Circuit, Complete Mathematical Ledger**

| Field | Value |
|-------|-------|
| Version | v5.2α |
| Status | All constants defined; zero placeholders remain |
| Blocking gaps | NONE |
| Ready for | Compilation, spin-up, full validation suite |

Authoritative runtime source: `config/params.yml` (hot-loaded; POST `/api/update` to rewrite).

## Key v5.2α deltas from v5.1

| Item | v5.1 | v5.2α |
|------|------|-------|
| `C_iso` | 0.087 F | **0.071 F** (depth-corrected, d=14 mi) |
| `C_total` | 0.131 F | **0.115 F** |
| `Omega_max` | 5.0 rad/s | **4.9 rad/s** (E_break verified) |
| Island depth `d_iso` | — | **14.0 mi** (MT-inferred) |
| Grounding `Z_g` | — | **2.8 Ω** |
| Mass exchange `K_m` | — | **0.0013 kg·m⁻³·s⁻¹** |
| Rotor inertia `I_rot` | — | **2.3×10²⁴ kg·m²** |
| Firmament n(z) | — | n′, n″ exponential profiles |
| Validation checks | 17 | **18** (2 pending: gravity, jerks) |
| Sun/Moon nodes | — | 33 mi dia, z=3000 mi, Moon Δφ=11.1° |

## File manifest

```
config/params.yml          # Complete ledger — ZERO undefined constants
config/node_table.csv      # Sun, Moon, 4 islands
spectra/luminary_lines.csv # Emission lines (391–636 nm)
validation/
  geomagnetic_jerks.csv
  lat_resonance.md
observations/              # Perspective Tool datasets
src/earth/cosmology/       # Python engine (fields, engine, validation)
src/earth/cosmology/imf_hook.py  # OMNI2 Bz (engineering, non-blocking)
public/data/cosmology/     # Baked edge JSON
```

## Open engineering tasks (non-blocking)

1. IMF coupling amplitude — `imf_hook.py` OMNI2 Bz tuning
2. GPU AMR for island patches

## API

- `GET /api/params` — full ledger
- `GET /api/cosmology/state` — live telemetry
- `GET /api/validate` — 18-check suite
- `GET /api/cosmology/spectra` — luminary emission lines

See `scripts/bake_cosmology.py` to rebake edge assets after parameter changes.