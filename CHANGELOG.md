# Changelog

## v2.9 (changes since v2.8)

### Fixed
- **Webcam export**: exporting a webcam list failed with "No valid streams found" (all webcams are YouTube and YouTube entries were skipped). YouTube entries are now exported as `youtube.com/watch` links, playable from bouquets with **ytdlpwrapper** (`enigma2-plugin-extensions-ytdlpwrapper`).
- Webcam bouquets get their own file names (`tvgarden_webcams_<name>`) instead of overwriting the TV bouquet of the same country.

### Installer
- Installs `enigma2-plugin-extensions-ytdlpwrapper` (ipk: recommends it).

### Updater
- Also reads three-part versions (e.g. 2.9.1) from `installer.sh`, for future releases.

### Other
- `CHANGELOG.md` added.

## v2.8 (changes since v2.7)

### Fixed: features broken by the current data format
- **Search**: stream links are read from the nested `sources` object used by the data, so results play again. Entries without a stream are skipped, YouTube webcams are included (`[YT]` label), country names are shown correctly.
- **Search loading**: uses `all.json` (2 downloads instead of ~490 requests), runs in the background and stops when the screen is closed.
- **Export ALL Database** (single file and multi-file): finds the channels again and runs in the background; bouquets are reloaded afterwards.

### YouTube
- yt-dlp is started once per stream with a format fallback chain (live webcams only offer HLS; the old one-format-per-run approach hit the timeouts).
- Uses YouTube's `android_vr` client first: works without a JavaScript runtime (deno is not available for most receivers). Falls back to the default clients; uses node/bun/quickjs when installed.
- yt-dlp found on PATH or as `python3 -m yt_dlp`; longer timeouts for slow receivers.
- The player shows the real yt-dlp error instead of a generic message.

### Player
- Service type follows the **Player** setting: 4097 by default, 5002 (ExtePlayer3) / 5001 (GStreamer) only when ServiceApp is installed.
- No longer closes itself while zapping (evStopped); cleanup runs once.
- Timers keep working on DreamOS (eTimer connections kept alive).
- YouTube resolution runs in a worker thread; stale results are ignored.
- Removed no-op hardware acceleration / buffer size code.

### Screens and keys
- Removed the undefined `TVGardenActions` keymap context: **MENU** opens the channel menu, **YELLOW** refreshes Countries and Categories.
- All colour key labels used by the XML skins are provided.
- Channel logos and country flags download in the background; logos are decoded at widget size and no longer disappear before decoding.
- UK flag fixed (`uk` → `gb`); **Show Flags** / **Show Logos** honoured.
- Fallback (class) skins show the title and status line.
- Channel list export honours **Enable Export**, **List Position** and the bouquet channel limit.

### Cache, config and settings
- Damaged cache files are downloaded again instead of returning nothing.
- Category data and the category list expire; **Enable Cache**, **Cache Size** and **User Agent** are honoured; atomic, locked cache writes; non-JSON responses are not cached.
- Leaving the plugin keeps the cache; the main menu opens without network access and preselects the **Default View**.
- `config.export()` no longer creates a directory named after the target file.
- Config and favorites are saved atomically.
- New setting: **Cache Duration** (15 min - 7 days).
- Removed settings that had no effect: hardware acceleration, buffer size, memory optimization.

### Favorites and bouquets
- Favorites are removed by stream URL or id (removal failed for some entries).
- A damaged `favorites.json` is kept as `favorites.json.broken_<time>` instead of being overwritten.
- `bouquets.tv` no longer gets entries glued to the previous line; **List Position** (top/bottom) is honoured.
- Multi-file export: safe file names, `0` = no split, empty sub-bouquets skipped.
- "Remove bouquets" clearly removes all TV Garden bouquets.

### Updater
- Version check and installer use the same repository (OwnerPlugins).
- Installer downloaded over verified HTTPS (no more `--no-check-certificate | sh`).
- Update check and installation run in the background; only the latest backup is kept in `/tmp`.

### Installer and packaging
- Installer installs all requirements: `ca-certificates`, `python3-yt-dlp` (pip fallback), ServiceApp and players.
- Correct Python 3 detection; package lists updated once; exact "already installed" check.
- `BRANCH=` variable to install another branch (e.g. `develop`).
- ipk: `Depends: python3-core`, `Recommends: ca-certificates, python3-yt-dlp, ServiceApp`.
- `postrm`: removed the UTF-8 BOM that broke the script.
- `postinst`: compiles `TVGarden.po` (correct gettext domain), sane permissions, no skin symlinks, removes developer scripts.
- **Python 3 only**: clear message on Python 2 images; dead Python 2 code removed.

### Repository and CI
- `.gitignore`: `lib/` and `var/` anchored to the root (they ignored every new file under `usr/lib`).
- PEP8 workflow no longer rewrites tabs inside strings and never pushes from pull requests.
- README rewritten to match the plugin.
