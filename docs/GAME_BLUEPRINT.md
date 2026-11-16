# GAME BLUEPRINT — block_juggle_cleanroom_01

Generated from `ORDER.md` (sha256 `4cfa3443f41ba20a…`) at 2026-11-16T04:53:43Z.
This file is generated, not hand-written: edit `ORDER.md` and push to change it.

## Your idea, as the studio understood it
> Build a 100% original, commercial-grade Clean-Room 3D/2.5D Crystal Grid Cascade Puzzle game in Godot 4.7.2 inspired by https://play.google.com/store/apps/details?id=com.block.juggle (`com.block.juggle`). Include an 8x8 interactive board, 3-piece spawn tray, Juggle/Hold swap slot, row/column/3x3 clear combos, 4-hit armored crystal blocks, 30 progressive levels (verifying Levels 1, 8, 16, 30 in QA), 5 endless mode stages, 12 unified mobile UI screens with >=56px touch targets, 4-bus procedural audio, and callback-verified AdMob + Play Billing IAP catalog.

## Mapping
| Idea signal | Studio decision |
| :--- | :--- |
| Requested genre | `block_puzzle` → engine family `block_puzzle` |
| Theme detected | `crystal` |
| Difficulty detected | `standard` (mercy rescue at 2 placements, Crystal Fever at 3x combo) |
| Category | `level_by_level` |

## Theme palette (drives icons, launcher art and 3D tint)
| Role | Hex |
| :--- | :--- |
| Background | `#0F172A` |
| Surface | `#1E293B` |
| Primary | `#38BDF8` |
| Accent | `#00E676` |
| Reward | `#FBBF24` |
| Danger | `#F43F5E` |

Piece names: Crystal Cube, Frost Block, Prism Tile, Shard Crystal

## Board & progression
- Board 8x8, 3-piece tray, Juggle Hold slot
- 30 levels (milestones [1, 3, 6, 8, 10, 16, 30]), 5 endless chunks
- Armored blocks take 4 hits

## Monetisation catalog
| SKU | Price | Contents |
| :--- | :--- | :--- |
| `starter_gem_pouch` | ₹89 | 120 crystals |
| `handful_of_gems` | ₹169 | 260 crystals |
| `gem_jar` | ₹299 | 500 crystals + 1 hammer |
| `gem_chest` | ₹499 | 900 crystals + 3 hammers |
| `mega_crystal_bundle` | ₹699 | 1500 crystals + 5 juggles |
| `vault_of_plenty` | ₹849 | 2500 crystals + all boosters |

## Ad policy
- Mid-move interstitials: **0**
- Interstitials only from level 3, 180s cooldown
- Rewarded ads are opt-in only
