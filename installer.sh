#!/bin/bash

version='3.0'
echo "TVGarden Version: $version"
echo "Streaming installer (no /tmp, no HDD, no external devices)"
# command telnet =
# wget -q --no-check-certificate "https://raw.githubusercontent.com/OwnerPlugins/TVGarden/main/installer.sh" -O - | /bin/sh
BRANCH="${BRANCH:-main}"

# Determina il percorso corretto dei plugin
if [ -d /usr/lib/enigma2/python/Plugins ]; then
    PLUGINBASE=/usr/lib/enigma2/python/Plugins/Extensions
elif [ -d /usr/lib64/enigma2/python/Plugins ]; then
    PLUGINBASE=/usr/lib64/enigma2/python/Plugins/Extensions
else
    PLUGINBASE=/usr/lib/enigma2/python/Plugins/Extensions
fi
PLUGINPATH="$PLUGINBASE/TVGarden"

echo "Plugin path: $PLUGINPATH"

# Verifica Python 3
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: TVGarden requires Python 3"
    exit 1
fi

# Avviso se yt-dlp manca (opzionale)
if ! command -v yt-dlp >/dev/null 2>&1 && ! python3 -c "import yt_dlp" >/dev/null 2>&1; then
    echo "WARNING: yt-dlp is missing. YouTube channels and webcams will not play."
    echo "         Install it with: opkg install python3-yt-dlp  (or: pip3 install yt-dlp)"
fi

# Rimuovi vecchia installazione
echo "Removing old installation (if any)..."
rm -rf "$PLUGINPATH"

# Crea la directory base
mkdir -p "$PLUGINBASE"

# URL
TARBALL_URL="https://github.com/OwnerPlugins/TVGarden/archive/refs/heads/$BRANCH.tar.gz"
IPK_URL="https://raw.githubusercontent.com/OwnerPlugins/upload/main/oe2.0/lululla/enigma2-plugin-extensions-tvgarden_${version}_all.ipk"

# Download ed estrazione in streaming
echo "Downloading and extracting TVGarden directly to $PLUGINPATH..."
if command -v wget >/dev/null 2>&1; then
    wget -q --no-check-certificate -O - "$TARBALL_URL" | tar -xz -C "$PLUGINBASE" --strip-components=7 "TVGarden-$BRANCH/usr/lib/enigma2/python/Plugins/Extensions/TVGarden" 2>/dev/null
    STREAM_OK=$?
elif command -v curl >/dev/null 2>&1; then
    curl -fsSL "$TARBALL_URL" | tar -xz -C "$PLUGINBASE" --strip-components=7 "TVGarden-$BRANCH/usr/lib/enigma2/python/Plugins/Extensions/TVGarden" 2>/dev/null
    STREAM_OK=$?
else
    echo "ERROR: neither wget nor curl found."
    STREAM_OK=1
fi

if [ $STREAM_OK -ne 0 ] || [ ! -f "$PLUGINPATH/plugin.py" ]; then
    echo "Tarball streaming failed, trying IPK fallback..."
    rm -rf "$PLUGINPATH"
    IPKPATH="$PLUGINBASE/TVGarden-$version.ipk"
    TMPEXTRACT="$PLUGINBASE/.tvgarden_extract"
    rm -rf "$TMPEXTRACT"
    mkdir -p "$TMPEXTRACT"

    if command -v wget >/dev/null 2>&1; then
        wget -q --no-check-certificate -O "$IPKPATH" "$IPK_URL"
    elif command -v curl >/dev/null 2>&1; then
        curl -fsSL -o "$IPKPATH" "$IPK_URL"
    else
        echo "ERROR: cannot download IPK fallback."
        exit 1
    fi

    if [ -f "$IPKPATH" ]; then
        python3 - "$IPKPATH" "$TMPEXTRACT" <<'PYEOF'
import io, sys, tarfile
data = open(sys.argv[1], "rb").read()
if not data.startswith(b"!<arch>\n"):
    sys.exit("not an ipk")
pos = 8
while pos + 60 <= len(data):
    header = data[pos:pos + 60]
    name = header[:16].decode().strip().rstrip("/")
    size = int(header[48:58].decode().strip())
    body = data[pos + 60:pos + 60 + size]
    if name.startswith("data.tar"):
        with tarfile.open(fileobj=io.BytesIO(body)) as tar:
            if hasattr(tarfile, "data_filter"):
                tar.extractall(sys.argv[2], filter="data")
            else:
                tar.extractall(sys.argv[2])
        sys.exit(0)
    pos += 60 + size + (size % 2)
sys.exit("data.tar not found in ipk")
PYEOF
        # Sposta il plugin estratto nella posizione finale
        if [ -d "$TMPEXTRACT/usr/lib/enigma2/python/Plugins/Extensions/TVGarden" ]; then
            rm -rf "$PLUGINPATH"
            mv "$TMPEXTRACT/usr/lib/enigma2/python/Plugins/Extensions/TVGarden" "$PLUGINPATH"
        elif [ -d "$TMPEXTRACT/usr/lib64/enigma2/python/Plugins/Extensions/TVGarden" ]; then
            rm -rf "$PLUGINPATH"
            mv "$TMPEXTRACT/usr/lib64/enigma2/python/Plugins/Extensions/TVGarden" "$PLUGINPATH"
        else
            echo "ERROR: Could not find TVGarden in extracted IPK."
            find "$TMPEXTRACT" -name "plugin.py" -maxdepth 6
            rm -rf "$TMPEXTRACT" "$IPKPATH"
            exit 1
        fi
        rm -rf "$TMPEXTRACT"
        rm -f "$IPKPATH"
    else
        echo "ERROR: Failed to download IPK fallback."
        exit 1
    fi
fi

# Verifica installazione
if [ ! -f "$PLUGINPATH/plugin.py" ] || [ ! -f "$PLUGINPATH/__init__.py" ]; then
    echo "ERROR: Installation failed. Missing critical files in $PLUGINPATH"
    ls -la "$PLUGINPATH" 2>/dev/null
    exit 1
fi

# Imposta permessi
echo "Setting permissions..."
chmod -R 755 "$PLUGINPATH"
find "$PLUGINPATH" -name "*.py" -exec chmod 644 {} \;
find "$PLUGINPATH" -name "*.sh" -exec chmod 755 {} \;

# Rimuovi tool di sviluppo non necessari sul decoder
rm -f "$PLUGINPATH/update_translations.py" "$PLUGINPATH/translate_utils.py"

sync

echo ""
echo "#########################################################"
echo "#               INSTALLED SUCCESSFULLY                  #"
echo "#                developed by LULULLA                   #"
echo "#               https://corvoboys.org                   #"
echo "#########################################################"
echo "#       restart Enigma2 to use the new version          #"
echo "#########################################################"
echo "Plugin path: $PLUGINPATH"
echo "Plugin version: $version"
echo "YT-DLP: $(yt-dlp --version 2>/dev/null || python3 -m yt_dlp --version 2>/dev/null || echo missing)"
exit 0
