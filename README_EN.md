### | [RU](./README.md) | EN |

# Inspired by Wotstat-vegetation mod

# WotStat Spotting

A mod that visualizes your own vehicle's spotting geometry — the 6
visibility checkpoints and 2 view range ports the game's spotting
mechanics actually use — as an in-world overlay, plus angle-based
exposure hints relative to your own hull orientation. A teaching tool
for positioning and angling, in the same spirit as an armor viewer,
but for spotting instead of armor.


## Installation

No release has been published yet. Build it from source:

1. Clone this repository.
2. Run `./build.sh -v <version> -d` (see `AGENTS.md`'s Build Commands
   section for details; Python 2 required).
3. Copy the resulting `wotstat.spotting_<version>.mtmod` into
   `WoT/mods/{CURRENT_GAME_VERSION}/`.

Once a release exists it will be published at
[GitHub Releases](https://github.com/WetSilhouette/wotstat-spotting/releases/latest).

## Usage

* `F4` - Show/Hide the spotting overlay.
* `F5` - Show/Hide checkpoint/port name labels (off by default — the
  colors alone are usually enough once you know what they mean).

### Marker meaning

**Checkpoints** (6 small spheres) — colored by angle-based exposure
relative to *your own* hull's current forward direction. This is a
heuristic, cosmetic hint, not a prediction of whether any specific
enemy can currently see you — it never uses or needs enemy data of any
kind:

* `Orange` - facing (within ~45° of your hull's forward direction).
* `Yellow` - side.
* `Green` - rear-facing.

**View range ports** (2 larger spheres):

* `Red` - the chassis port. Static and hull-relative — always sits at
  your tank's single highest collision point.
* `Magenta` - the turret port. The *only* one of the 8 markers that
  tracks live turret rotation; all 6 checkpoints and the chassis port
  are rigidly fixed to the hull even as your turret swings.

## What this mod will never do

* **No enemy vehicle data of any kind** — no checkpoint or view-port
  visualization for any vehicle but your own, spotted or not, ever,
  under any toggle or "debug" framing.
* **No real-time "am I currently spotted by a specific enemy"
  prediction.** The server never gives your client an unspotted
  enemy's position, so there is no legitimate data path for this.
