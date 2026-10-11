#!/bin/bash

# TV Garden Installer for Enigma2
# wget -q --no-check-certificate "https://raw.githubusercontent.com/OwnerPlugins/TVGarden/main/installer.sh" -O - | /bin/sh

version='3.0'
echo "TVGarden Version: $version"
echo "Changelog:"
echo "- Fix receiver freeze during Check for Updates (updates plugin files only)"
echo "- Safe install: only ca-certificates and yt-dlp are installed automatically"
echo "- Optional players/plugins (ServiceApp, exteplayer3, gstplayer, ffmpeg, ytdlpwrapper): EXTRAS=1"
echo "- No package manager calls inside the ipk install scripts"
echo "- Fix install path on images with /usr/lib64"
echo "- Fix download failing on images whose wget cannot verify HTTPS"
echo "- Bouquet reload no longer reloads the service list (lamedb)"
echo ""

# Branch to install (default: main). Example for testing:
#   wget -qO- https://raw.githubusercontent.com/OwnerPlugins/TVGarden/develop/installer.sh | BRANCH=develop /bin/sh
#
# By default only the plugin files and yt-dlp are installed. Players and
# Enigma2 plugins (ServiceApp, exteplayer3, gstplayer, ffmpeg, ytdlpwrapper)
# are NOT installed automatically: installing them while Enigma2 is running
# can upgrade libraries / image packages under the running GUI. To install
# them too, run with EXTRAS=1 (best from telnet/SSH, then restart):
#   wget -qO- .../installer.sh | EXTRAS=1 /bin/sh
#
# UPDATE_ONLY=1 (used by the plugin's own updater): plugin files only,
# no package manager at all.
BRANCH="${BRANCH:-main}"
EXTRAS="${EXTRAS:-0}"
UPDATE_ONLY="${UPDATE_ONLY:-0}"
TMPPATH=/tmp/TVGarden-install
FILEPATH=/tmp/TVGarden-$BRANCH.tar.gz
SRCDIR="$TMPPATH/TVGarden-$BRANCH"

echo "Starting TVGarden installation (branch: $BRANCH)..."

# Install where Enigma2 really loads plugins from (some aarch64 images
# have /usr/lib64 but keep Enigma2 in /usr/lib)
if [ -d /usr/lib/enigma2/python/Plugins ]; then
    PLUGINPATH=/usr/lib/enigma2/python/Plugins/Extensions/TVGarden
elif [ -d /usr/lib64/enigma2/python/Plugins ]; then
    PLUGINPATH=/usr/lib64/enigma2/python/Plugins/Extensions/TVGarden
else
    PLUGINPATH=/usr/lib/enigma2/python/Plugins/Extensions/TVGarden
fi

cleanup() {
    echo "Cleaning up temporary files..."
    [ -d "$TMPPATH" ] && rm -rf "$TMPPATH"
    [ -f "$FILEPATH" ] && rm -f "$FILEPATH"
}

detect_os() {
    if [ -f /var/lib/dpkg/status ]; then
        OSTYPE="DreamOs"
        STATUS="/var/lib/dpkg/status"
    elif [ -f /etc/opkg/opkg.conf ] || [ -f /var/lib/opkg/status ]; then
        OSTYPE="OE"
        STATUS="/var/lib/opkg/status"
    else
        OSTYPE="Unknown"
        STATUS=""
    fi
    echo "Detected OS type: $OSTYPE"
}

detect_os

cleanup
mkdir -p "$TMPPATH"

# Download $1 to $2. Many receivers cannot verify HTTPS with wget (BusyBox
# wget, or GNU wget without a CA path) even with ca-certificates installed,
# so try every verified method first and only then fall back to wget
# without certificate check.
fetch() {
    url=$1
    out=$2
    rm -f "$out"
    if command -v wget >/dev/null 2>&1 && wget -q -O "$out" "$url" 2>/dev/null && [ -s "$out" ]; then
        return 0
    fi
    if command -v curl >/dev/null 2>&1 && curl -fsSL -o "$out" "$url" 2>/dev/null && [ -s "$out" ]; then
        return 0
    fi
    if python3 -c "import sys, urllib.request; urllib.request.urlretrieve(sys.argv[1], sys.argv[2])" "$url" "$out" 2>/dev/null && [ -s "$out" ]; then
        return 0
    fi
    if command -v wget >/dev/null 2>&1; then
        echo "WARNING: HTTPS certificate could not be verified on this box, downloading without verification"
        if wget -q --no-check-certificate -O "$out" "$url" && [ -s "$out" ]; then
            return 0
        fi
    fi
    rm -f "$out"
    return 1
}

# Refresh the package lists once
FEED_UPDATED=0
update_feeds() {
    [ "$FEED_UPDATED" = "1" ] && return
    echo "Updating package lists..."
    case "$OSTYPE" in
        "DreamOs") apt-get update </dev/null >/dev/null 2>&1 ;;
        "OE") opkg update </dev/null >/dev/null 2>&1 ;;
    esac
    FEED_UPDATED=1
}

is_installed() {
    [ -n "$STATUS" ] && grep -qx "Package: $1" "$STATUS" 2>/dev/null
}

install_pkg() {
    pkg=$1
    if is_installed "$pkg"; then
        echo "$pkg already installed"
        return 0
    fi
    update_feeds
    echo "Installing $pkg..."
    case "$OSTYPE" in
        "DreamOs")
            apt-get install -y --no-install-recommends "$pkg" </dev/null >/dev/null 2>&1 && return 0 ;;
        "OE")
            opkg install --no-install-recommends "$pkg" </dev/null >/dev/null 2>&1 && return 0 ;;
        *)
            echo "Cannot install $pkg on unknown OS type"
            return 1 ;;
    esac
    echo "Could not install $pkg, continuing anyway..."
    return 1
}

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: TVGarden requires a Python 3 image (Python 2 is not supported)"
    exit 1
fi
echo "Python: $(python3 --version 2>&1)"

ytdlp_ok() {
    command -v yt-dlp >/dev/null 2>&1 || python3 -c "import yt_dlp" >/dev/null 2>&1
}

OPTIONAL_PKGS="enigma2-plugin-systemplugins-serviceapp exteplayer3 gstplayer ffmpeg enigma2-plugin-extensions-ytdlpwrapper"

if [ "$UPDATE_ONLY" = "1" ]; then
    echo "Update mode: plugin files only, no packages are installed"
else
    if ! command -v wget >/dev/null 2>&1; then
        install_pkg wget || echo "wget not available, using curl/python3 for downloads"
    fi

    # Needed to download over verified HTTPS
    install_pkg ca-certificates

    # yt-dlp: needed for YouTube channels and webcams (pure Python package)
    if ! ytdlp_ok; then
        install_pkg python3-yt-dlp
    fi
    if ! ytdlp_ok && command -v pip3 >/dev/null 2>&1; then
        echo "yt-dlp not in the feed, installing it with pip..."
        pip3 install -U yt-dlp </dev/null >/dev/null 2>&1 || \
            pip3 install -U --break-system-packages yt-dlp </dev/null >/dev/null 2>&1
    fi
    if ytdlp_ok; then
        echo "yt-dlp OK: $(yt-dlp --version 2>/dev/null || python3 -m yt_dlp --version 2>/dev/null)"
    else
        echo "WARNING: yt-dlp is missing: YouTube channels and webcams will not play"
        echo "         Install it with: opkg install python3-yt-dlp  (or: pip3 install yt-dlp)"
    fi

    # Optional players / plugins: only on request (EXTRAS=1)
    if [ "$OSTYPE" = "OE" ]; then
        MISSING=""
        for pkg in $OPTIONAL_PKGS; do
            is_installed "$pkg" || MISSING="$MISSING $pkg"
        done
        if [ -n "$MISSING" ]; then
            if [ "$EXTRAS" = "1" ]; then
                echo "Installing optional packages:$MISSING"
                for pkg in $MISSING; do
                    install_pkg "$pkg"
                done
            else
                echo "Optional packages not installed:$MISSING"
                echo "  (ExtePlayer3/GStreamer player options and playing webcams from bouquets)"
                echo "  To install them: opkg install$MISSING"
            fi
        fi
    fi
fi

echo "Downloading TVGarden..."
if ! fetch "https://github.com/OwnerPlugins/TVGarden/archive/refs/heads/$BRANCH.tar.gz" "$FILEPATH"; then
    echo "Failed to download TVGarden package!"
    echo "Check the internet connection and DNS of the receiver (github.com must be reachable)."
    cleanup
    exit 1
fi

echo "Extracting package..."
tar -xzf "$FILEPATH" -C "$TMPPATH"
if [ $? -ne 0 ]; then
    echo "Failed to extract TVGarden package!"
    cleanup
    exit 1
fi

echo "Installing plugin files..."
mkdir -p "$PLUGINPATH"

# TROVA E COPIA IL CONTENUTO CORRETTO - METODO ROBUSTO
SOURCE_DIR=""

# Cerca il contenuto del plugin in vari percorsi possibili
for search_path in \
    "$SRCDIR/usr/lib/enigma2/python/Plugins/Extensions/TVGarden" \
    "$SRCDIR/usr/lib64/enigma2/python/Plugins/Extensions/TVGarden" \
    "$SRCDIR/TVGarden" \
    "$SRCDIR"
do
    if [ -d "$search_path" ] && [ -f "$search_path/plugin.py" ]; then
        SOURCE_DIR="$search_path"
        echo "Found plugin source at: $SOURCE_DIR"
        break
    fi
done

if [ -n "$SOURCE_DIR" ]; then
    # Copia tutto il contenuto della directory trovata
    echo "Copying plugin files from $SOURCE_DIR to $PLUGINPATH"
    cp -r "$SOURCE_DIR"/* "$PLUGINPATH/" 2>/dev/null
    
    # Verifica che i file critici siano stati copiati
    if [ $? -eq 0 ] && [ -f "$PLUGINPATH/plugin.py" ]; then
        echo "Successfully copied plugin files"
        
        # Imposta i permessi corretti
        chmod -R 755 "$PLUGINPATH"
        find "$PLUGINPATH" -name "*.py" -exec chmod 644 {} \;
        find "$PLUGINPATH" -name "*.sh" -exec chmod 755 {} \;
        # Developer tools are not needed on the receiver
        rm -f "$PLUGINPATH/update_translations.py" "$PLUGINPATH/translate_utils.py"
    else
        echo "Error: Failed to copy plugin files!"
        echo "Attempting fallback method..."
        
        # Fallback: estrai direttamente nella destinazione
        tar -xzf "$FILEPATH" --strip-components=1 -C "$PLUGINPATH" --wildcards "*TVGarden/*" 2>/dev/null
    fi
else
    echo "Could not find plugin files in extracted archive!"
    echo "Available directories:"
    find "$TMPPATH" -type f -name "*.py" | head -10
    cleanup
    exit 1
fi

sync

echo "Verifying installation..."
if [ -f "$PLUGINPATH/plugin.py" ] && [ -f "$PLUGINPATH/__init__.py" ]; then
    echo "Plugin successfully installed: $PLUGINPATH"
    echo "Main files:"
    ls -la "$PLUGINPATH/plugin.py" "$PLUGINPATH/__init__.py" 2>/dev/null
else
    echo "ERROR: Plugin installation failed!"
    echo "Missing critical files in: $PLUGINPATH"
    echo "Directory contents:"
    ls -la "$PLUGINPATH/" 2>/dev/null
    cleanup
    exit 1
fi

cleanup
sync

box_type=$(sed -n '1p' /etc/hostname 2>/dev/null || echo "Unknown")
# distro_value=$(grep '^distro=' "$FILE" 2>/dev/null | awk -F '=' '{print $2}')
# distro_version=$(grep '^version=' "$FILE" 2>/dev/null | awk -F '=' '{print $2}')
distro_value="Unknown"
distro_version="Unknown"
if [ -r /etc/os-release ]; then
    distro_value=$(grep '^NAME=' /etc/os-release 2>/dev/null | cut -d'"' -f2)
    distro_version=$(grep '^VERSION_ID=' /etc/os-release 2>/dev/null | cut -d'"' -f2)
elif [ -r /etc/issue ]; then
    distro_value=$(head -n 1 /etc/issue 2>/dev/null | awk '{print $1}')
    distro_version=$(head -n 1 /etc/issue 2>/dev/null | awk '{print $2}')
elif [ -r /etc/vtiversion.info ]; then
    distro_value=$(head -n 1 /etc/vtiversion.info 2>/dev/null)
elif [ -r /etc/issue.net ]; then
    distro_value=$(head -n 1 /etc/issue.net 2>/dev/null | awk '{print $1}')
    distro_version=$(head -n 1 /etc/issue.net 2>/dev/null | awk '{print $2}')
fi

[ -z "$distro_value" ] && distro_value="Unknown"
[ -z "$distro_version" ] && distro_version="Unknown"
python_vers=$(python3 --version 2>&1)

cat <<EOF

#########################################################
#               INSTALLED SUCCESSFULLY                  #
#                developed by LULULLA                   #
#               https://corvoboys.org                   #
#########################################################
#       restart Enigma2 to use the new version          #
#########################################################
Debug information:
BOX MODEL: $box_type
OS SYSTEM: $OSTYPE
PYTHON: $python_vers
IMAGE NAME: ${distro_value:-Unknown}
IMAGE VERSION: ${distro_version:-Unknown}
PLUGIN PATH: $PLUGINPATH
PLUGIN VERSION: $version
YT-DLP: $(yt-dlp --version 2>/dev/null || python3 -m yt_dlp --version 2>/dev/null || echo missing)
EOF
exit 0