<h1 align="center">📺 TV Garden Plugin for Enigma2</h1>

[![Version](https://img.shields.io/badge/Version-2.8-blue.svg)](https://github.com/OwnerPlugins/TVGarden)
[![Enigma2](https://img.shields.io/badge/Enigma2-Plugin-ff6600.svg)](https://www.enigma2.net)
[![Python](https://img.shields.io/badge/Python-3%20only-blue.svg)](https://www.python.org)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

[![Visitors](https://komarev.com/ghpvc/?username=OwnerPlugins&label=Repository%20Views&color=blueviolet)](https://github.com/OwnerPlugins)
[![Donate](https://img.shields.io/badge/_-Donate-red.svg?logo=githubsponsors&labelColor=555555&style=for-the-badge)](https://ko-fi.com/lululla)
[![Donate](https://img.shields.io/badge/_-Donate-green.svg?logo=githubsponsors&labelColor=555555&style=for-the-badge)](https://paypal.me/belfagor2005)

<img src="https://play-lh.googleusercontent.com/TuMoS5RrGwz6xmyyYkA56eXukRHNNd2JgldA0wpzVFxiQDAAf9NLuKkTacl29_ltEbr4YvshNOauntxGlrvb=w240-h480-rw" alt="Icon image">

**Free IPTV channels and live webcams** for Enigma2 receivers: thousands of TV channels from **170+ countries**, browsable by country or category, plus **live webcams** from around the world. Featuring **smart caching**, **search across TV and webcams**, **YouTube playback via yt-dlp** and **native Enigma2 bouquet export**.

---

## 📺 Screenshots

<table>
  <tr>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Belfagor2005/TVGarden/main/screen/screen1.png" height="220">
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Belfagor2005/TVGarden/main/screen/screen2.png" height="220">
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Belfagor2005/TVGarden/main/screen/screen3.png" height="220">
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Belfagor2005/TVGarden/main/screen/screen4.png" height="220">
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Belfagor2005/TVGarden/main/screen/screen5.png" height="220">
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Belfagor2005/TVGarden/main/screen/screen6.png" height="220">
    </td>
  </tr>
</table>

---

## ✨ Key Features

### 🌍 Content
- **TV channels by country** (170+ countries, with flags) and **by category**
- **Live webcams** by country or by category
- **Dynamic categories** - read from the data source, no hardcoded lists
- **YouTube channels and webcams** - resolved with `yt-dlp` (no JavaScript runtime needed)

### ▶️ Player
- **Player selection** - Auto (Enigma2 default player), ExtePlayer3 or GStreamer (via ServiceApp)
- **Channel zapping** - CH+/CH- (or Up/Down) through the current list
- **On-screen info** - channel name, position and country
- **Automatic retry** - restarts a stream that ends unexpectedly (up to 3 times)
- **Problematic streams filtered** - DASH / DRM (Widevine, PlayReady) entries are skipped on export

### 🔍 Search
- **Unified search** across TV channels and webcams (`[TV]` / `[WEB]` / `[YT]` labels)
- **Virtual keyboard** (GREEN) or **number keys** (T9 style)
- **Loads in the background** - the screen stays responsive while data loads

### ⭐ Favorites & Bouquets
- **Favorites** - add/remove from any channel list or from search
- **Export** - current list, favorites, single channel or the **whole database**
- **Multi-file export** - one container bouquet with a sub-bouquet per country,
  large countries split into parts
- **Bouquet position** - new bouquets added at the top or bottom of your list
- **Clean removal** - remove every TV Garden bouquet in one step

### ⚙️ System
- **Smart caching** - configurable duration and size, works offline with cached data
- **Auto skin detection** - HD / FHD / WQHD
- **Logging** - configurable level, viewable from Settings
- **Updates** - check and install from the plugin, with automatic backup/restore
- **Multi-language interface**

---

## 📊 Technical Specifications

| Component | Specification |
|-----------|--------------|
| **TV Channels** | About 6,800 (from 170+ countries; the data is updated regularly) |
| **Webcams** | About 4,000 |
| **Categories** | Read dynamically from the data source |
| **Player Engines** | Auto (4097) / ExtePlayer3 (5002) / GStreamer (5001) |
| **YouTube** | yt-dlp, `android_vr` client first (works without deno/node) |
| **Cache** | Disk cache in `/tmp/tvgarden_cache`, 15 min to 7 days, 10-5000 files |
| **Skins** | HD (1280x720), FHD (1920x1080), WQHD (2560x1440) |
| **Python Compatibility** | Python 3 only (Python 2 images are not supported) |

---

## 📦 Requirements

> **Python 3 images only.** TV Garden does not run on Python 2 images
> (and yt-dlp, needed for YouTube channels and webcams, requires Python 3.9+).

The installer script installs the required packages automatically. To install them by hand:

```bash
opkg update
opkg install ca-certificates python3-yt-dlp
opkg install enigma2-plugin-systemplugins-serviceapp exteplayer3 gstplayer ffmpeg
```

If your feed has no `python3-yt-dlp` package:

```bash
opkg install python3-pip && pip3 install -U yt-dlp
```

| Package | Needed for |
|---------|-----------|
| `ca-certificates` | Secure (HTTPS) downloads of data and updates |
| `python3-yt-dlp` | YouTube channels and all webcams |
| `serviceapp`, `exteplayer3`, `gstplayer` | The ExtePlayer3 / GStreamer player options |
| `ffmpeg` | Some stream formats |

### ⚙️ Player and ServiceApp

- **Auto** (default): plays with the standard Enigma2 player (service 4097).
  If ServiceApp is installed it may handle 4097 too, using the
  **Player IPTV** choice in **Menu → Settings → System → ServiceApp**.
- **ExtePlayer3** / **GStreamer**: use ServiceApp directly (services 5002 / 5001).
  Without ServiceApp the plugin falls back to the standard player.

---

## ⚙️ Settings

All options are in **Main Menu → Settings** (BLUE in the main menu).
They are stored in `/etc/enigma2/tvgarden/config.json`.

### Browser
| Setting | Values | Default |
|---------|--------|---------|
| Default View | Countries / Categories / Favorites (cursor position in the main menu) | Countries |
| Max channels for country | 100 - 5000, or All | 1000 |
| Show Flags | Yes / No | Yes |
| Show Logos | Yes / No | Yes |

### Player
| Setting | Values | Default |
|---------|--------|---------|
| Player | Auto / ExtePlayer3 / GStreamer | Auto |

### Export
| Setting | Values | Default |
|---------|--------|---------|
| Enable Export | Yes / No | Yes |
| List Position | Top / Bottom (where new bouquets go in your list) | Bottom |
| Bouquet Name Prefix | text | TVGarden |
| Max Channels for Bouquet | 50 - 5000, or All | 500 |
| Max Channels for Sub-Bouquet | 100 - 5000, or All (no split) | 500 |

### Network
| Setting | Values | Default |
|---------|--------|---------|
| User Agent | text | `TVGarden-Enigma2-Updater/<version>` |
| Connection Timeout | 10 - 300 seconds | 30 |

### Cache
| Setting | Values | Default |
|---------|--------|---------|
| Enable Cache | Yes / No | Yes |
| Cache Duration | 15 min / 1 hour / 6 hours / 24 hours / 7 days | 1 hour |
| Cache Size | 10 - 5000 files | 500 |
| Refresh Method | Clear Cache / Force Refresh (what YELLOW "Refresh" does) | Clear Cache |
| Force Refresh on Browsing | Yes / No (always download fresh lists) | No |
| Force Refresh on Export | Yes / No (always download a fresh database) | No |

### Search
| Setting | Values | Default |
|---------|--------|---------|
| Max Search Results | 10 - 5000, or All | 500 |

### Logging
| Setting | Values | Default |
|---------|--------|---------|
| Log Level | Debug / Info / Warning / Error / Critical | Info |
| Log to File | Yes / No | Yes |
| View Log File / Clear Log Files Now | press OK | |

**Check for Updates** is also available at the bottom of Settings.

---

## 🎮 Usage Guide

### Main Menu

```
Browse by Country      - TV channels by country
Browse by Category     - TV channels by category
Webcams by Country     - Live webcams by country
Webcams by Category    - Live webcams by category
Favorites              - Your saved channels
Search                 - Search across TV + webcams
Settings               - Plugin configuration
Check for Updates      - Check for plugin updates
About                  - Plugin information
```

Main menu keys: **OK/GREEN** select, **YELLOW** refresh data, **BLUE** settings, **RED/EXIT** close.

### Countries / Categories
```
OK / GREEN      - Open the selected country or category
YELLOW          - Refresh the list
EXIT / RED      - Back
```

### Channel List
```
OK / GREEN      - Play selected channel
YELLOW          - Add / remove favorite
BLUE            - Export the current list to a bouquet
MENU            - Channel menu (play, favorite, info, export)
EXIT / RED      - Back
```

### Favorites
```
OK / GREEN      - Play selected channel
YELLOW          - Options (info, remove, clear all, export, export database, remove bouquets)
BLUE            - Export all favorites to a bouquet
EXIT / RED      - Back
```

### Search
```
GREEN           - Virtual keyboard
0-9             - Type with number keys (T9 style)
OK              - Play selected result
YELLOW          - Add / remove favorite
BLUE            - Clear search
EXIT / RED      - Back
```

### Player
```
CHANNEL +/- (Up/Down) - Zap between channels
OK              - Show / hide the info bar
INFO            - Channel information
EXIT / STOP     - Close player
```

YouTube channels and webcams show *"Resolving YouTube stream..."* first;
on a receiver this can take 10-60 seconds.

### Tips
1. **Max channels for country**: 250-500 for faster loading on slow receivers
2. **Cache**: keep it enabled; use YELLOW "Refresh" when you want fresh data
3. **Whole database export**: use the Multi-File option, it keeps Enigma2 fast

### Bouquet Export
1. **Current list** (BLUE in a channel list): `userbouquet.tvgarden_<country or category>.tv`
2. **Favorites** (BLUE in Favorites): `userbouquet.tvgarden_<prefix>_favorites.tv`
3. **Whole database, single file**: `userbouquet.tvgarden_<prefix>_all_channels.tv`
4. **Whole database, multi-file**:
   - `userbouquet.tvgarden_<prefix>_complete_container.tv` (parent)
   - `subbouquet.tvgarden_<country>.tv` for each country
   - countries larger than *Max Channels for Sub-Bouquet* are split (`_part1`, `_part2`, ...)
5. YouTube entries are not exported (they need yt-dlp, which bouquets cannot use)
6. Bouquets are reloaded automatically; all files are in `/etc/enigma2/`

---

## 📥 Installation

```bash
# Install (or update) with the installer script - recommended
wget -qO- "https://raw.githubusercontent.com/OwnerPlugins/TVGarden/main/installer.sh" | /bin/sh

# Restart the Enigma2 GUI
killall -9 enigma2
```

The installer installs the requirements (see above), downloads the plugin
over verified HTTPS and prints a summary, including the yt-dlp version.

To test another branch (for example `develop`):

```bash
wget -qO- "https://raw.githubusercontent.com/OwnerPlugins/TVGarden/develop/installer.sh" | BRANCH=develop /bin/sh
```

If the download fails with a certificate error, install `ca-certificates` first.

---

## 📁 Data Source

Channel and webcam data comes from an external public dataset:

➡ **https://github.com/OwnerPlugins/famelack-data**

Sources are organized as:

```
tv/raw/countries_metadata.json     → country list (names, channel counts)
tv/raw/countries/{code}.json       → TV channels by country
tv/raw/categories/{id}.json        → TV channels by category
tv/raw/categories/all.json         → all TV channels (search, database export)
webcams/raw/...                    → same structure for webcams
```

Each channel lists its streams under `sources` (`streams`, `youtube`, ...).
Categories are **read dynamically** from the GitHub API (cached, so the
API's hourly request limit is not a problem in normal use).

---

## 🔧 Technical Architecture

### File Structure
```
TVGarden/
├── __init__.py
├── plugin.py          - main menu
├── helpers.py         - URLs, stream parsing, bouquet helpers, logging
├── browser/           - countries, categories, channels, favorites, search, about
├── player/            - player screen
├── utils/             - cache, config, favorites, settings, updater, yt-dlp helper
├── skins/             - hd / fhd / wqhd
├── images/, icons/
└── locale/            - translations
```

### Cache
- Downloaded lists are stored gzip-compressed in `/tmp/tvgarden_cache/`
- Expire after the configured **Cache Duration**; damaged files are downloaded again
- The cache is kept between sessions (until the receiver restarts or you refresh)

### Player
- Service type follows the **Player** setting (4097 / 5002 / 5001)
- YouTube links are resolved with yt-dlp in the background
- Flags, logos, YouTube resolution, search loading and database exports run in the background

---

## 🔍 Search System

### Features
- **TV + Webcams** - unified search across both sources
- **Virtual keyboard** or **number keys**
- Matches channel name, description, group and source (`tv` / `webcams`)
- **Configurable limit** - 10 to 5000 results, or all (default: 500)
- **Cache-aware** - uses cached data when available

---

## ⭐ Favorites

### Features
- **Unlimited favorites**, no duplicates (checked by stream URL)
- **Export** to a bouquet, single or all
- **Safe storage** - a damaged favorites file is kept as `favorites.json.broken_<time>`
  instead of being overwritten

### Storage
File: `/etc/enigma2/tvgarden/favorites/favorites.json`

```json
[
  {
    "id": "unique_hash",
    "name": "Channel Name",
    "stream_url": "https://...",
    "country": "it",
    "added": 1734567890
  }
]
```

---

## 🐛 Troubleshooting

### Common Issues
| Issue | Solution |
|-------|----------|
| **"YouTube stream not available"** | Read the reason under the message. "yt-dlp is not installed": `opkg install python3-yt-dlp` (or `pip3 install -U yt-dlp`). Other errors: update yt-dlp with `pip3 install -U yt-dlp` |
| **Channels not loading** | Check the internet connection, press YELLOW (Refresh), check the log |
| **Player shows nothing** | Try another channel (many free streams go offline), or another **Player** in Settings |
| **ExtePlayer3/GStreamer option has no effect** | Install `enigma2-plugin-systemplugins-serviceapp` |
| **Only "All" in categories** | GitHub API not reachable or rate limited; try again later |
| **Bouquets not appearing** | Restart the Enigma2 GUI |
| **Certificate errors on install/update** | `opkg install ca-certificates` |

### Cache
- **Refresh**: YELLOW in the main menu, Countries or Categories
- **Always fresh data**: enable "Force Refresh on Browsing/Export" in Settings
- **Location**: `/tmp/tvgarden_cache/`

### Logs & Debugging
- **View Logs**: Settings → View Log File
- **Log Level**: set to Debug in Settings when troubleshooting
- **Location**: `/tmp/tvgarden_cache/tvgarden.log`
- **YouTube problems**: `grep YouTube /tmp/tvgarden_cache/tvgarden.log | tail`
- **Crash at start**: `/tmp/tvgarden_crash.log`

---

## 📄 License

```
TV Garden Plugin for Enigma2
Copyright (C) 2025 TV Garden Development Team

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
```

---

## 🙏 Credits & Acknowledgments

### Core Development
- **Original Concept**: Lululla (TV Garden Project)
- **Upstream Fork**: Belfagor2005
- **Data Source**: [https://github.com/OwnerPlugins/famelack-data](https://github.com/OwnerPlugins/famelack-data)
- **Fork & Webcams Support**: OwnerPlugins

### Special Thanks
- Enigma2 community for testing & feedback
- All contributors and translators

---

## 📞 Support & Resources

- **Fork**: [https://github.com/OwnerPlugins/TVGarden](https://github.com/OwnerPlugins/TVGarden)
- **Data Source**: [https://github.com/OwnerPlugins/famelack-data](https://github.com/OwnerPlugins/famelack-data)

**Enjoy streaming with TV Garden!** 📺

*Last Updated: 2026* | *Version: 2.8*

