<h1 align="center">📺 TV Garden Plugin for Enigma2</h1>

![Visitors](https://komarev.com/ghpvc/?username=Belfagor2005&label=Repository%20Views&color=blueviolet)
[![Version](https://img.shields.io/badge/Version-2.3-blue.svg)](https://github.com/Belfagor2005/TVGarden)
[![Enigma2](https://img.shields.io/badge/Enigma2-Plugin-ff6600.svg)](https://www.enigma2.net)
[![Python](https://img.shields.io/badge/Python-2.7%2B-blue.svg)](https://www.python.org)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python package](https://github.com/Belfagor2005/TVGarden/actions/workflows/pylint.yml/badge.svg)](https://github.com/Belfagor2005/TVGarden/actions/workflows/pylint.yml)
[![Ruff Status](https://github.com/Belfagor2005/TVGarden/actions/workflows/ruff.yml/badge.svg)](https://github.com/Belfagor2005/TVGarden/actions/workflows/ruff.yml)
[![GitHub stars](https://img.shields.io/github/stars/Belfagor2005/TVGarden?style=social)](https://github.com/Belfagor2005/TVGarden/stargazers)
[![Donate](https://img.shields.io/badge/_-Donate-red.svg?logo=githubsponsors&labelColor=555555&style=for-the-badge)](Maintainers.md#maintainers "Donate")

<img src="https://play-lh.googleusercontent.com/TuMoS5RrGwz6xmyyYkA56eXukRHNNd2JgldA0wpzVFxiQDAAf9NLuKkTacl29_ltEbr4YvshNOauntxGlrvb=w240-h480-rw" alt="Icon image">

**Professional IPTV Streaming Solution** for Enigma2 receivers with access to **50,000+ channels** from **150+ countries** across **29 categories**. Featuring **smart caching**, **hardware acceleration**, and **native Enigma2 bouquet export**.

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

### 🚀 Performance Optimization
- **Hardware Acceleration** - Configurable toggle for H.264/H.265 streams
- **Buffer Size Control** - 512KB to 8MB configurable buffer
- **Smart Player Selection** - Auto, ExtePlayer3, or GStreamer
- **Memory Optimization** - Efficient RAM usage (~50MB)

### 🌍 Global Content Access
- **150+ Countries** with national flags display
- **29 Content Categories** (News, Sports, Movies, Music, Kids, etc.)
- **50,000+ Channels** regularly updated

### ⚙️ Advanced Technology
- **Smart Configuration System** - 20+ configurable parameters
- **Smart Caching** - Enable/Disable, Configurable Size, Force Refresh options
- **Auto-Skin Detection** - HD/FHD/WQHD resolution support
- **File Logging System** - Configurable log level and file output

### 🔄 Integration & Export
- **Dual Bouquet Export System** - Single-file simplicity or multi-file hierarchical structure
- **Smart Channel Splitting** - Configurable max channels per sub-bouquet file (default 500)
- **Hierarchical Bouquet Architecture** - Parent container with country-specific sub-bouquets
- **Configurable Export** - Bouquet name prefix, max channels per bouquet, export confirmation
- **Favorites Management** - Add/Remove channels, view info, and export directly
- **Complete Bouquet Management** - Tag-based removal of all bouquet files (`.tvgarden_*`)

### 🛡️ Reliability & Safety
- **DRM/Crash Protection** - Filtered problematic streams (DASH, Widevine, etc.)
- **Offline Cache** - Browse cached channels without internet
- **Automatic Updates** - Check for plugin updates with backup/restore

### 🔍 Enhanced User Experience
- **Channel Zapping** - CH+/CH- navigation between channels in player
- **Real-time Search** - Virtual keyboard with case-insensitive search across all channels
- **Performance Stats** - HW acceleration and buffer info in player overlay
- **Multi-language Interface** - Support for international users

---

## 📊 Technical Specifications

| Component | Specification |
|-----------|--------------|
| **Total Channels** | 50,000+ |
| **Countries** | 150+ |
| **Categories** | 29 |
| **Configuration Parameters** | 20+ |
| **Player Engines** | Auto / ExtePlayer3 / GStreamer |
| **Buffer Size Range** | 512KB - 8MB |
| **Cache Size** | Configurable (10-5000 items) |
| **Memory Usage** | ~50MB |
| **Load Time (cached)** | <5 seconds |
| **Stream Compatibility** | ~70% success rate |
| **Python Compatibility** | 2.7+ (Enigma2 optimized) |

---

## ⚙️ Configuration System

### Player Settings
```ini
player = auto               # auto / exteplayer3 / gstplayer
```

### Performance Settings
```ini
use_hardware_acceleration = true  # Enable HW acceleration
buffer_size = 2048                # Buffer size in KB (512-8192)
memory_optimization = true        # Memory optimization
```

### Display Settings
```ini
show_flags = true          # Show country flags
show_logos = false         # Show channel logos (configurable)
```

### Cache Settings
```ini
cache_enabled = true       # Enable caching
cache_size = 500          # Maximum cache items (10-5000)
refresh_method = clear_cache  # clear_cache or force_refresh
force_refresh_browsing = false # Force fresh data when browsing
force_refresh_export = false   # Force fresh data for exports
```

### Export Settings
```ini
export_enabled = true     # Enable bouquet export
bouquet_name_prefix = TVGarden  # Bouquet name prefix
max_channels_for_bouquet = 100  # Max channels per bouquet (0=all)
max_channels_for_sub_bouquet = 500 # Max channels per sub-bouquet
auto_refresh_bouquet = false    # Auto-refresh bouquet after export
confirm_before_export = true    # Confirm before exporting
list_position = bottom    # top or bottom in Enigma2 list
```

### Browser Settings
```ini
max_channels = 500        # Max channels per country (0=all)
default_view = countries  # countries / categories / favorites
sort_by = name            # Sort channels by name / country / category
```

### Network Settings
```ini
user_agent = TVGarden-Enigma2/1.0  # Custom user agent
connection_timeout = 30   # Network connection timeout (10-300s)
download_timeout = 60     # Download timeout for large files (30-600s)
```

### Logging Settings
```ini
log_level = INFO          # DEBUG / INFO / WARNING / ERROR / CRITICAL
log_to_file = true        # Enable file logging
```

### Search Settings
```ini
search_max_results = 200  # Max results in search (10-1000)
search_real_time = true   # Real-time search while typing
```

### Bouquet Management
```ini
bouquet_auto_reload = true # Auto-reload bouquets after export
```

---

## 🎮 Usage Guide

### Navigation Controls

**Browser Controls:**
```
OK / GREEN      - Play selected channel
EXIT / RED      - Back / Exit
YELLOW          - Context menu (Remove/Export)
BLUE            - Export favorites to bouquet
```

**Favorites Browser:**
```
OK / GREEN      - Play selected channel
EXIT / RED      - Back / Exit
YELLOW          - Options (Remove/Info/Export)
BLUE            - Export ALL to Enigma2 bouquet
ARROWS          - Navigate channels
```

**Player Controls:**
```
CHANNEL +/-     - Zap between channels
OK              - Show channel info + performance stats
EXIT            - Close player
```

### Performance Tips
1. **Buffer Size**: 2MB-4MB for stable connections
2. **HW Acceleration**: ON for H.264/H.265 streams
3. **Max Channels per Country**: 250-500 for faster loading
4. **Cache**: Enable for normal use, disable for testing fresh data

### Bouquet Export Workflow
1. **Single-File Export**: Best for small lists (<1000 channels)
2. **Multi-File (Hierarchical)**: Recommended for complete database export
   - Creates `userbouquet.tvgarden_complete_container.tv` (parent)
   - Creates `subbouquet.tvgarden_[country].tv` for each country
   - Countries with >500 channels are split into parts (e.g., `_part1`)
3. **Export Options**: Access via Yellow button → Export ALL Database
4. **Location**: `/etc/enigma2/*.tvgarden_*`
5. **Restart**: Enigma2 to see new bouquets

---

## 📥 Installation

```bash
# Download and install via script (Recommended)
wget -q --no-check-certificate "https://raw.githubusercontent.com/Belfagor2005/TVGarden/main/installer.sh" -O - | /bin/sh

# Restart Enigma2
reboot
```

---

## 🔧 Technical Architecture

### File Structure
```
TVGarden/
├── __init__.py
├── plugin.py
├── helpers.py
├── browser/
├── player/
├── utils/
├── skins/
├── icons/
├── locale/
├── install.sh
└── README.md
```

### Cache System Features
- **Configurable Enable/Disable**: Toggle entire cache system
- **Force Refresh Options**: Fresh data for browsing or export operations
- **Memory + Disk Cache**: Dual-layer for performance
- **Smart Management**: Configurable size limits

### Player Features
- **Hardware Acceleration**: Automatic detection for H.264/H.265 streams
- **Buffer Management**: Configurable buffer size applied to service reference
- **Performance Settings**: Integrated into player initialization

---

## 🔍 Search System

### Features
- **Real-time Case-Insensitive Search** - Instant results as you type
- **Virtual Keyboard** - Full text input support
- **Smart Filtering** - YouTube/DRM content automatically filtered
- **Configurable Limits** - 10-1000 results (default: 200)
- **Cache-aware** - Uses cached data when available

---

## ⭐ Favorites & Export System

### Features
- **Unlimited Favorites Storage**
- **Smart Deduplication** - Prevents adding duplicate channels
- **Hierarchical Export** - Single or multi-file bouquet creation
- **Complete Management** - Add, remove, info, and export options
- **Bouquet Removal** - Clean removal of all `.tvgarden_*` files

### Storage Format
```json
[
  {
    "id": "unique_hash",
    "name": "Channel Name",
    "stream_url": "stream_url",
    "country": "Country Code",
    "added": 1734567890
  }
]
```

---

## 🐛 Troubleshooting

### Common Issues
| Issue | Solution |
|-------|----------|
| **Channels not loading** | Check internet, clear cache (`Settings → Clear Logs`), restart plugin |
| **Player won't start** | Verify GStreamer/ExtePlayer3 installation, check URL format |
| **Search not working** | Clear cache, check network connection to GitHub |
| **Bouquets not appearing** | Restart Enigma2 after export |
| **High memory usage** | Reduce cache size, limit max channels per country |

### Cache Management
- **Clear Cache**: Via Settings screen → "Clear Log Files Now"
- **Force Fresh Data**: Enable "Force Refresh on Browsing/Export" in Cache Settings
- **Location**: `/tmp/tvgarden_cache/`

### Logs & Debugging
- **View Logs**: `Settings → View Log File`
- **Log Level**: Adjust in Settings (DEBUG for troubleshooting)
- **Location**: `/tmp/tvgarden_cache/tvgarden.log`

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
- **Data Source**: [https://github.com/Belfagor2005/famelack-data](https://github.com/Belfagor2005/famelack-data)
- **Plugin Development**: TV Garden Development Team
- **Hierarchical Export**: Inspired by Vavoo Plugin architecture

### Special Thanks
- Enigma2 community for testing & feedback
- All contributors and translators

---

## 📞 Support & Resources

### Documentation & Support
- **GitHub Issues**: [Report bugs/request features](https://github.com/Belfagor2005/TVGarden/issues)
- **Releases**: [Latest versions and changelog](https://github.com/Belfagor2005/TVGarden/releases)

**Enjoy optimized streaming with TV Garden!** 📺⚡

*Last Updated: 2025-12-17* | *Version: 1.7* | *Code Review: Configuration cleanup completed*
```
