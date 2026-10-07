#!/bin/bash

# TV Garden Installer for Enigma2
# wget -q "https://raw.githubusercontent.com/OwnerPlugins/TVGarden/main/installer.sh" -O - | /bin/sh

version='2.7'
echo "TVGarden Version: $version"
echo "Changelog:"
echo "- Add Webcams support (by Country and by Category)"
echo "- Add Webcams integration in Search (TV + Webcams unified)"
echo "- Add dynamic category loading from GitHub API (no hardcoded lists)"
echo "- Add multi-source support (tv / webcams) with media_type propagation"
echo "- Add ServiceApp + ytdlpwrapper integration for YouTube streams"
echo "- Add embed-to-watch URL conversion for YouTube webcams"
echo "- Add opkg .list fix compatibility"
echo "- Fix Skin HD font sizes and item heights for 1280x720"
echo "- Fix ActionMap 'menu' action on ChannelsBrowser"
echo "- Fix Main menu layout for HD resolution"
echo "- Update README with webcams documentation"
echo "- Add youtube streaming on player"
echo "- Fix Problematic Channels"
echo ""

TMPPATH=/tmp/TVGarden-install
FILEPATH=/tmp/TVGarden-main.tar.gz

echo "Starting TVGarden installation..."

if [ ! -d /usr/lib64 ]; then
    PLUGINPATH=/usr/lib/enigma2/python/Plugins/Extensions/TVGarden
else
    PLUGINPATH=/usr/lib64/enigma2/python/Plugins/Extensions/TVGarden
fi

cleanup() {
    echo "Cleaning up temporary files..."
    [ -d "$TMPPATH" ] && rm -rf "$TMPPATH"
    [ -f "$FILEPATH" ] && rm -f "$FILEPATH"
    [ -d "/tmp/TVGarden-main" ] && rm -rf "/tmp/TVGarden-main"
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

if ! command -v wget >/dev/null 2>&1; then
    echo "Installing wget..."
    case "$OSTYPE" in
        "DreamOs")
            apt-get update && apt-get install -y wget || { echo "Failed to install wget"; exit 1; }
            ;;
        "OE")
            opkg update && opkg install wget || { echo "Failed to install wget"; exit 1; }
            ;;
        *)
            echo "Unsupported OS type. Cannot install wget."
            exit 1
            ;;
    esac
fi

if python --version 2>&1 | grep -q '^Python 3\.'; then
    echo "Python3 image detected"
    PYTHON="PY3"
    Packagesix="python3-six"
    # Packagerequests="python3-requests"
else
    echo "Python2 image detected"
    PYTHON="PY2"
    # Packagerequests="python-requests"
    Packagesix="python-six"
fi

install_pkg() {
    local pkg=$1
    if [ -z "$STATUS" ] || ! grep -qs "Package: $pkg" "$STATUS" 2>/dev/null; then
        echo "Installing $pkg..."
        case "$OSTYPE" in
            "DreamOs")
                apt-get update && apt-get install -y "$pkg" || { echo "Could not install $pkg, continuing anyway..."; }
                ;;
            "OE")
                opkg update && opkg install "$pkg" || { echo "Could not install $pkg, continuing anyway..."; }
                ;;
            *)
                echo "Cannot install $pkg on unknown OS type, continuing..."
                ;;
        esac
    else
        echo "$pkg already installed"
    fi
}

if [ "$PYTHON" = "PY3" ]; then
    install_pkg "$Packagesix"
fi
# install_pkg "$Packagerequests"

# Needed to download over verified HTTPS
install_pkg "ca-certificates"

if [ "$OSTYPE" = "OE" ]; then
    echo "Installing additional multimedia packages..."
    for pkg in ffmpeg gstplayer exteplayer3 enigma2-plugin-systemplugins-serviceapp; do
        install_pkg "$pkg"
    done
fi

echo "Downloading TVGarden..."
wget 'https://github.com/OwnerPlugins/TVGarden/archive/refs/heads/main.tar.gz' -O "$FILEPATH"
if [ $? -ne 0 ]; then
    echo "Failed to download TVGarden package!"
    echo "If this is a certificate error, install the 'ca-certificates' package."
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
    "$TMPPATH/TVGarden-main/TVGarden" \
    "$TMPPATH/TVGarden-main" \
    "$TMPPATH/TVGarden-main/usr/lib/enigma2/python/Plugins/Extensions/TVGarden" \
    "$TMPPATH/TVGarden-main/usr/lib64/enigma2/python/Plugins/Extensions/TVGarden"
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

FILE="/etc/image-version"
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
python_vers=$(python --version 2>&1)

cat <<EOF

#########################################################
#               INSTALLED SUCCESSFULLY                  #
#                developed by LULULLA                   #
#               https://corvoboys.org                   #
#########################################################
#           your Device will RESTART Now                #
#########################################################
^^^^^^^^^^Debug information:
BOX MODEL: $box_type
OS SYSTEM: $OSTYPE
PYTHON: $python_vers
IMAGE NAME: ${distro_value:-Unknown}
IMAGE VERSION: ${distro_version:-Unknown}
PLUGIN PATH: $PLUGINPATH
PLUGIN VERSION: $version
EOF
exit 0