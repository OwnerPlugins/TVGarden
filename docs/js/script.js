'use strict';

// ============================================================
// Repo configuration (OwnerPlugins/famelack-data)
// ============================================================
const REPO_OWNER  = 'OwnerPlugins';
const REPO_NAME   = 'famelack-data';
const REPO_BRANCH = 'main';   // se serve, cambia in 'master'

function repoBase() {
    return `https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${REPO_BRANCH}`;
}

function isYouTubeUrl(url) {
    if (!url || typeof url !== 'string') return false;
    const u = url.toLowerCase();
    return u.includes('youtube.com') || u.includes('youtu.be') || u.includes('youtube-nocookie.com');
}

function extractYouTubeId(url) {
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
    const match = url.match(regExp);
    return (match && match[2].length === 11) ? match[2] : null;
}

// Porting esatto di extract_stream_url del plugin Python
function extractStreamUrl(channel) {
    if (!channel || typeof channel !== 'object') {
        return { url: null, foundIn: null, isYouTube: false };
    }
    const sources = channel.sources;
    if (sources && typeof sources === 'object') {
        for (const key of ['streams', 'iptv', 'youtube', 'iframe']) {
            const arr = sources[key];
            if (!Array.isArray(arr)) continue;
            for (const u of arr) {
                if (typeof u !== 'string' || !u.trim()) continue;
                if (key === 'iframe' && !isYouTubeUrl(u)) continue;
                return { url: u.trim(), foundIn: `sources.${key}`, isYouTube: isYouTubeUrl(u) };
            }
        }
    }
    for (const key of ['iptv_urls', 'youtube_urls', 'stream_urls']) {
        const arr = channel[key];
        if (!Array.isArray(arr)) continue;
        for (const u of arr) {
            if (typeof u === 'string' && u.trim()) {
                return { url: u.trim(), foundIn: key, isYouTube: isYouTubeUrl(u) };
            }
        }
    }
    const flat = channel.url || channel.stream_url;
    if (typeof flat === 'string' && flat.trim()) {
        return { url: flat.trim(), foundIn: 'url', isYouTube: isYouTubeUrl(flat) };
    }
    return { url: null, foundIn: null, isYouTube: false };
}

function flattenCountryBlock(block) {
    if (Array.isArray(block)) return block;
    if (block && typeof block === 'object') {
        for (const field of ['channels', 'items', 'streams', 'data']) {
            if (Array.isArray(block[field])) return block[field];
        }
    }
    return [];
}

function parseFamelackPayload(data, countryCode = null) {
    if (!data) return [];
    if (Array.isArray(data)) return data;
    if (typeof data === 'object') {
        if (countryCode) {
            const candidates = [countryCode.toUpperCase(), countryCode.toLowerCase()];
            for (const key of candidates) {
                if (data[key]) return flattenCountryBlock(data[key]);
            }
            for (const key of Object.keys(data)) {
                if (key.toUpperCase() === countryCode.toUpperCase()) {
                    return flattenCountryBlock(data[key]);
                }
            }
        }
        for (const field of ['channels', 'items', 'streams', 'data']) {
            if (Array.isArray(data[field])) return data[field];
        }
    }
    return [];
}

class OwnersPluginsTV {
    constructor() {
        this.channels = [];
        this.channelGroups = {};
        this.hls = null;
        this.currentChannel = null;
        this.favorites = new Set();
        this.epgData = [];
        this.uploadHistory = [];
        this.lastPlaylist = null;
        this.uploadedPlaylists = {};
        this.repoCache = {};                 // cache in-memory per liste repo
        this.videoPlayer = document.getElementById('videoPlayer');
        this.loadingIndicator = document.getElementById('loadingIndicator');
        this.notification = document.getElementById('notification');
        this.refreshButton = document.getElementById('refreshButton');
        this.toggleSidebarButton = document.getElementById('toggleSidebarButton');
        this.toggleSidebarIcon = document.getElementById('toggleSidebar');
        this.fullscreenButton = document.getElementById('fullscreenButton');
        this.themeToggle = document.getElementById('themeToggle');
        this.searchInput = document.getElementById('searchInput');
        this.sidebar = document.querySelector('.sidebar');
        this.epgGuide = document.getElementById('epgGuide');
        this.epgProgress = document.getElementById('epgProgress');
        this.videoContainer = document.querySelector('.video-container');
        this.uploadModal = document.getElementById('uploadModal');
        this.fileUpload = document.getElementById('fileUpload');
        this.urlUpload = document.getElementById('urlUpload');
        this.uploadFileButton = document.getElementById('uploadFileButton');
        this.uploadUrlButton = document.getElementById('uploadUrlButton');
        this.clearHistoryButton = document.getElementById('clearHistoryButton');
        this.uploadClose = document.getElementById('uploadClose');
        this.uploadHistoryContainer = document.getElementById('uploadHistory');
        this.playlistStats = document.getElementById('playlistStats');
        this.mainContent = document.querySelector('.main-content');
        // Repo controls
        this.repoMediaType = document.getElementById('repoMediaType');
        this.repoListType = document.getElementById('repoListType');
        this.repoLoadList = document.getElementById('repoLoadList');
        this.repoListContainer = document.getElementById('repoListContainer');
        this.isUploading = false;
        this.filterStatus = null;
        this.init();
    }

    async init() {
        this.showWelcomeNotification();
        this.setupEventListeners();
        this.loadFavorites();
        this.loadUploadHistory();
        await this.loadLastPlaylist();
        this.displayChannels();
        this.updatePlaylistStats();
        this.updatePlayerSize();
        this.uploadModal.classList.add('show');
        this.registerServiceWorker();
    }

    showWelcomeNotification() {
        const message = `Welcome to Owners Plugins!\nYour gateway to endless entertainment.\n\nNote: This player does not host or provide any media. Please load your own playlists (M3U, JSON, or TXT) to start watching.`;
        this.notification.textContent = message;
        this.notification.classList.add('show');
        setTimeout(() => this.notification.classList.remove('show'), 6000);
    }

    updatePlayerSize() {
        if (this.channels.length === 0 && this.epgData.length === 0) {
            this.sidebar.classList.add('hidden');
            this.epgGuide.classList.remove('visible');
            this.mainContent.classList.add('no-playlist');
        } else {
            this.mainContent.classList.remove('no-playlist');
            this.sidebar.classList.remove('hidden');
        }
    }

    async loadLastPlaylist() {
        const saved = localStorage.getItem('lastPlaylist');
        if (!saved) { this.updatePlayerSize(); return; }
        this.lastPlaylist = JSON.parse(saved);

        if (this.lastPlaylist.type === 'url') {
            await this.fetchM3U(this.lastPlaylist.value);
        } else if (this.lastPlaylist.type === 'file' && this.uploadedPlaylists[this.lastPlaylist.value]) {
            this.channels = this.uploadedPlaylists[this.lastPlaylist.value];
            this.displayChannels();
            this.updatePlaylistStats();
        } else if (this.lastPlaylist.type === 'repo') {
            const parts = String(this.lastPlaylist.value).split('/');
            const [mediaType, listType, id] = parts;
            await this.loadRepoChannels(mediaType, listType, id === 'all' ? null : id, true);
        }
        this.updatePlayerSize();
    }

    // ============================================================
    // Normalize URLs
    // ============================================================
    normalizeUrl(url) {
        if (!url || typeof url !== 'string') return url;
        if (url.startsWith('http://')) {
            console.warn(`Converting HTTP to HTTPS: ${url}`);
            return url.replace('http://', 'https://');
        }
        if (/^http:\/\/\d+\.\d+\.\d+\.\d+/.test(url)) {
            console.warn(`IP-based URL detected: ${url}. Consider using a domain with HTTPS or a proxy.`);
        }
        return url;
    }

    // ============================================================
    // M3U / JSON / TXT parsing
    // ============================================================
    async fetchM3U(url) {
        try {
            const normalizedUrl = this.normalizeUrl(url);
            const response = await fetch(normalizedUrl, { cache: 'no-store' });
            if (!response.ok) throw new Error(`M3U fetch failed: ${response.status}`);
            const data = await response.text();
            this.channels = this.removeDuplicates(this.parseM3U(data));
            this.displayChannels();
            this.updatePlaylistStats();
            this.addToUploadHistory(url);
            this.lastPlaylist = { type: 'url', value: url };
            localStorage.setItem('lastPlaylist', JSON.stringify(this.lastPlaylist));
            this.showNotification('Playlist loaded successfully!');
            this.updatePlayerSize();
            return true;
        } catch (error) {
            console.error('M3U fetch failed:', error);
            this.showNotification('Failed to load M3U playlist. Ensure it uses HTTPS.');
            return false;
        }
    }

    async fetchEPG(url) {
        try {
            const normalizedUrl = this.normalizeUrl(url);
            const response = await fetch(normalizedUrl, { cache: 'no-store' });
            if (!response.ok) throw new Error(`EPG fetch failed: ${response.status}`);
            const data = await response.text();
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(data, 'text/xml');
            this.epgData = this.parseEPG(xmlDoc);
            this.channels.forEach(channel => {
                channel.programs = this.epgData.filter(p => p.channel === channel.id);
            });
            if (this.currentChannel) this.updateEPGDisplay(this.currentChannel);
            this.epgGuide.classList.add('visible');
            this.showNotification('EPG loaded successfully!');
        } catch (error) {
            console.warn('EPG loading failed:', error);
            this.showNotification('EPG unavailable');
            this.epgGuide.classList.remove('visible');
        }
    }

    parseM3U(data) {
        const lines = data.split('\n');
        const channels = [];
        let currentChannel = null;

        lines.forEach(line => {
            line = line.trim();
            if (!line) return;

            if (line.startsWith('#EXTINF:')) {
                currentChannel = {
                    duration: parseInt(line.split(',')[0].split(':')[1]) || -1,
                    title: line.split(',').slice(1).join(',').trim().replace(/\(.*?\)/g, '').trim() || 'Untitled',
                    id: '',
                    url: '',
                    group: 'Ungrouped',
                    logo: '',
                    programs: [],
                    status: 'unknown'
                };
                const logoMatch = line.match(/tvg-logo=["'](.*?)["']/i);
                currentChannel.logo = logoMatch ? this.normalizeUrl(logoMatch[1]) : './img/no-logo.png';
            } else if (line.startsWith('#EXTGRP:')) {
                currentChannel.group = line.split(':')[1].trim() || 'Ungrouped';
            } else if (line.startsWith('#EXTTVM:')) {
                currentChannel.id = line.split(':')[1].trim();
            } else if (currentChannel && !line.startsWith('#')) {
                currentChannel.url = this.normalizeUrl(line);
                channels.push(currentChannel);
                this.channelGroups[currentChannel.group] = this.channelGroups[currentChannel.group] || [];
                this.channelGroups[currentChannel.group].push(currentChannel);
                currentChannel = null;
            }
        });

        return channels.sort((a, b) =>
            a.group === b.group ? a.title.localeCompare(b.title) : a.group.localeCompare(b.group)
        );
    }

    removeDuplicates(channels) {
        const seen = new Set();
        return channels.filter(channel => {
            const key = `${channel.url}|${channel.title}`;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });
    }

    parseJSON(data) {
        let items;
        try {
            items = typeof data === 'string' ? JSON.parse(data) : data;
        } catch (e) {
            console.error('parseJSON: invalid JSON', e);
            return [];
        }

        const list = parseFamelackPayload(items);
        const channels = list.map((item, i) => this.toOwnersChannel(item, i, 'tv')).filter(Boolean);
        return this.removeDuplicates(channels.sort((a, b) =>
            a.group === b.group ? a.title.localeCompare(b.title) : a.group.localeCompare(b.group)
        ));
    }

    toOwnersChannel(item, index = 0, mediaType = 'tv') {
        const { url, foundIn, isYouTube } = extractStreamUrl(item);
        if (!url || !/^(https?|rtmp|rtsp):\/\//i.test(url)) return null;
        const country = String(item.country || '').toUpperCase();
        return {
            title: item.name || item.title || `Channel ${index + 1}`,
            url: url,
            group: item.group || item.category || country || 'Ungrouped',
            id: item.nanoid || item.id || `ch_${index}`,
            logo: item.logo || item.icon || item.image || './img/no-logo.png',
            language: Array.isArray(item.languages) ? item.languages.join(', ') : (item.language || ''),
            country: country,
            isYouTube: isYouTube,
            foundIn: foundIn,
            mediaType: mediaType,
            programs: [],
            status: 'unknown'
        };
    }

    parseTXT(data) {
        const lines = data.split('\n').filter(line => line.trim());
        const channels = lines.map((line, index) => ({
            title: `Channel ${index + 1}`,
            url: this.normalizeUrl(line.trim()),
            group: 'Imported',
            id: '',
            logo: './img/no-logo.png',
            programs: [],
            status: 'unknown'
        }));
        return this.removeDuplicates(channels);
    }

    parseEPG(xmlDoc) {
        const programs = [];
        const programmeElements = xmlDoc.getElementsByTagName('programme');

        for (const prog of Array.from(programmeElements)) {
            const start = new Date(prog.getAttribute('start').replace(/(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2}).*/, '$1-$2-$3T$4:$5:$6Z'));
            const stop = new Date(prog.getAttribute('stop').replace(/(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2}).*/, '$1-$2-$3T$4:$5:$6Z'));
            programs.push({
                channel: prog.getAttribute('channel'),
                startTime: start,
                endTime: stop,
                title: prog.getElementsByTagName('title')[0]?.textContent || 'Unknown',
                description: prog.getElementsByTagName('desc')[0]?.textContent?.trim() || 'No description',
                category: prog.getElementsByTagName('category')[0]?.textContent?.trim() || 'Uncategorized'
            });
        }
        return programs;
    }

    // ============================================================
    // Channel status (HEAD) + playlist stats
    // ============================================================
    async checkChannelStatus(channel) {
        return new Promise((resolve) => {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 5000);

            fetch(channel.url, {
                method: 'HEAD',
                signal: controller.signal,
                cache: 'no-store',
                mode: 'cors'
            })
            .then(response => {
                clearTimeout(timeout);
                channel.status = response.ok ? 'active' : 'offline';
                resolve();
            })
            .catch(() => {
                clearTimeout(timeout);
                channel.status = 'offline';
                resolve();
            });
        });
    }

    async updatePlaylistStats() {
        const total = this.channels.length;
        if (total === 0) {
            this.playlistStats.innerHTML = 'Total: 0 | Active: 0 | Offline: 0';
            return;
        }

        // Skip the expensive HEAD check for very large playlists
        if (total > 300) {
            this.playlistStats.innerHTML = `
                <span onclick="document.ownerspluginsTV.filterChannels('total')">Total: ${total}</span> | 
                <span title="Status check skipped for lists > 300 channels">Active: ? | Offline: ?</span>
            `;
            return;
        }

        await Promise.all(this.channels.map(channel => this.checkChannelStatus(channel)));
        const active = this.channels.filter(c => c.status === 'active').length;
        const offline = total - active;
        this.playlistStats.innerHTML = `
            <span onclick="document.ownerspluginsTV.filterChannels('total')">Total: ${total}</span> | 
            <span onclick="document.ownerspluginsTV.filterChannels('active')">Active: ${active}</span> | 
            <span onclick="document.ownerspluginsTV.filterChannels('offline')">Offline: ${offline}</span>
        `;
    }

    filterChannels(status) {
        this.filterStatus = status === this.filterStatus ? null : status;
        this.displayChannels(this.searchInput.value);
    }

    // ============================================================
    // Channel list rendering
    // ============================================================
    displayChannels(query = '') {
        const channelList = document.getElementById('channelList');
        channelList.innerHTML = '';

        if (this.channels.length === 0) {
            channelList.innerHTML = '<p>No channels available. Please upload a playlist.</p>';
            this.sidebar.classList.add('hidden');
            this.updatePlayerSize();
            return;
        }

        let filteredChannels = this.channels.filter(c =>
            c.title.toLowerCase().includes(query.toLowerCase()) ||
            c.group.toLowerCase().includes(query.toLowerCase())
        );

        if (this.filterStatus) {
            filteredChannels = filteredChannels.filter(c =>
                this.filterStatus === 'total' || c.status === this.filterStatus
            );
        }

        if (filteredChannels.length === 0) {
            channelList.innerHTML = '<p>No channels match your search or filter.</p>';
            return;
        }

        const grouped = filteredChannels.reduce((acc, channel) => {
            acc[channel.group] = acc[channel.group] || [];
            acc[channel.group].push(channel);
            return acc;
        }, {});

        const favoriteChannels = filteredChannels.filter(c => this.favorites.has(c.url));
        if (favoriteChannels.length > 0) {
            grouped['Favorites'] = favoriteChannels;
        }

        Object.keys(grouped).sort().forEach(group => {
            const groupDiv = document.createElement('div');
            groupDiv.className = 'channel-group';
            groupDiv.innerHTML = `<h3>${group}</h3>`;

            grouped[group].forEach(channel => {
                const channelDiv = document.createElement('div');
                channelDiv.className = `channel-item ${this.currentChannel?.url === channel.url ? 'active' : ''}`;
                channelDiv.innerHTML = `
                    <div class="channel-info">
                        <img src="${channel.logo}" class="channel-logo" alt="${channel.title} logo" onerror="this.src='./img/no-logo.png'">
                        <span class="channel-title">${channel.title}</span>
                    </div>
                `;
                const favoriteBtn = document.createElement('button');
                favoriteBtn.className = `favorite-btn ${this.favorites.has(channel.url) ? 'favorited' : ''}`;
                favoriteBtn.innerHTML = '★';
                favoriteBtn.onclick = (e) => {
                    e.stopPropagation();
                    this.toggleFavorite(channel.url);
                };
                channelDiv.appendChild(favoriteBtn);
                channelDiv.onclick = () => this.playChannel(channel.url);
                groupDiv.appendChild(channelDiv);
            });

            channelList.appendChild(groupDiv);
        });

        this.sidebar.classList.remove('hidden');
        this.updatePlayerSize();
    }

    // ============================================================
    // EPG
    // ============================================================
    updateEPGDisplay(channel) {
        if (this.epgData.length === 0) {
            this.epgGuide.classList.remove('visible');
            return;
        }

        const now = new Date();
        const current = channel?.programs?.find(p => now >= p.startTime && now <= p.endTime) || null;
        const next = channel?.programs?.find(p => p.startTime > now) || null;

        document.getElementById('epgCurrent').textContent = current ?
            `${current.title} - ${current.category}` : 'No current program';
        document.getElementById('epgTime').textContent = current ?
            `${current.startTime.toLocaleTimeString()} - ${current.endTime.toLocaleTimeString()}` : '';
        document.getElementById('epgNext').textContent = next ?
            `Next: ${next.title} - ${next.category}` : 'No next program';

        if (current) {
            const total = current.endTime - current.startTime;
            const elapsed = now - current.startTime;
            const progress = (elapsed / total) * 100;
            this.epgProgress.style.width = `${Math.min(progress, 100)}%`;
        } else {
            this.epgProgress.style.width = '0%';
        }

        this.epgGuide.classList.add('visible');
    }

    // ============================================================
    // Player
    // ============================================================
    playChannel(url) {
        if (this.currentChannel?.url === url) return;

        this.currentChannel = this.channels.find(c => c.url === url);
        if (!this.currentChannel) {
            this.showNotification('Channel not found');
            return;
        }

        this.updateChannelSelection();
        this.updateEPGDisplay(this.currentChannel);
        this.cleanupPlayer();

        this.loadingIndicator.classList.add('show');
        this.showNotification(`Now Playing: ${this.currentChannel.title}`);

        const normalizedUrl = this.normalizeUrl(url);
        
        // --- INIZIO MODIFICA PER YOUTUBE ---
        if (isYouTubeUrl(normalizedUrl)) {
            this.setupYouTube(normalizedUrl);
        } else if (Hls.isSupported() && normalizedUrl.includes('.m3u8')) {
            this.setupHLS(normalizedUrl);
        } else {
            this.setupNative(normalizedUrl);
        }
        // --- FINE MODIFICA ---
    }

    setupHLS(url) {
        this.hls = new Hls({
            debug: false,
            enableWorker: true,
            lowLatencyMode: true,
            backBufferLength: 90,
            maxBufferLength: 30,
            liveSyncDurationCount: 3,
            liveMaxLatencyDurationCount: 10,
            xhrSetup: (xhr) => {
                xhr.timeout = 10000;
                xhr.withCredentials = false;
            }
        });

        this.hls.on(Hls.Events.MEDIA_ATTACHED, () => {
            this.hls.loadSource(url);
        });

        this.hls.on(Hls.Events.MANIFEST_PARSED, () => {
            this.videoPlayer.play().catch(e => this.handleError(e, 'HLS Playback failed'));
        });

        this.hls.on(Hls.Events.ERROR, (event, data) => {
            if (data.fatal) {
                this.handleError(data, 'HLS Streaming error');
                this.setupNative(url);
            }
        });

        this.hls.attachMedia(this.videoPlayer);
    }

    setupYouTube(url) {
        const videoId = extractYouTubeId(url);
        if (!videoId) {
            this.handleError(null, 'Invalid YouTube URL');
            return;
        }

        // Nascondi il player standard
        this.videoPlayer.style.display = 'none';

        // Crea o riusa l'iframe
        let iframe = document.getElementById('youtubeIframe');
        if (!iframe) {
            iframe = document.createElement('iframe');
            iframe.id = 'youtubeIframe';
            iframe.style.width = '100%';
            iframe.style.height = '100%';
            iframe.style.border = 'none';
            iframe.style.position = 'absolute';
            iframe.style.top = '0';
            iframe.style.left = '0';
            iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture";
            iframe.allowFullscreen = true;
            this.videoContainer.appendChild(iframe);
        }

        // Carica il video con autoplay
        iframe.src = `https://www.youtube.com/embed/${videoId}?autoplay=1`;
        
        // Nascondi il caricamento
        this.loadingIndicator.classList.remove('show');
    }

    setupNative(url) {
        this.videoPlayer.src = url;
        this.videoPlayer.play().catch(e => this.handleError(e, 'Native playback failed'));
    }

    cleanupPlayer() {
        if (this.hls) {
            this.hls.destroy();
            this.hls = null;
        }
        
        // Rimuovi l'iframe di YouTube se esiste
        const iframe = document.getElementById('youtubeIframe');
        if (iframe) {
            iframe.remove();
        }
        
        // Ripristina il player standard
        this.videoPlayer.style.display = 'block';
        this.videoPlayer.pause();
        this.videoPlayer.removeAttribute('src');
        this.videoPlayer.load();
    }

    // ============================================================
    // Event listeners
    // ============================================================
    setupEventListeners() {
        this.videoPlayer.addEventListener('playing', () => {
            this.loadingIndicator.classList.remove('show');
        });
        this.videoPlayer.addEventListener('waiting', () => {
            this.loadingIndicator.classList.add('show');
        });
        this.videoPlayer.addEventListener('error', (e) => {
            this.handleError(e, 'Video error');
        });
        this.videoPlayer.addEventListener('stalled', () => {
            this.handleError(null, 'Video stalled');
        });
        this.videoPlayer.addEventListener('timeupdate', () => {
            if (this.currentChannel) this.updateEPGDisplay(this.currentChannel);
        });
        this.refreshButton.addEventListener('click', () => {
            if (this.currentChannel) {
                this.playChannel(this.currentChannel.url);
                this.showNotification('Channel refreshed!');
            }
        });
        this.toggleSidebarButton.addEventListener('click', () => {
            this.uploadModal.classList.add('show');
        });
        this.toggleSidebarIcon.addEventListener('click', () => {
            this.sidebar.classList.add('hidden');
        });
        this.fullscreenButton.addEventListener('click', () => this.toggleFullscreen());
        this.themeToggle.addEventListener('click', () => this.toggleTheme());
        this.searchInput.addEventListener('input', (e) => this.displayChannels(e.target.value));
        this.uploadFileButton.addEventListener('click', () => this.handleFileUpload());
        this.uploadUrlButton.addEventListener('click', () => this.handleUrlUpload());
        this.clearHistoryButton.addEventListener('click', () => this.clearHistory());
        this.uploadClose.addEventListener('click', () => {
            this.uploadModal.classList.remove('show');
            this.updatePlayerSize();
        });
        this.uploadModal.addEventListener('click', (e) => {
            if (e.target === this.uploadModal) {
                this.uploadModal.classList.remove('show');
                this.updatePlayerSize();
            }
        });
        this.fileUpload.addEventListener('change', () => {
            if (this.fileUpload.files.length > 0) this.handleFileUpload();
        });

        // ============ REPO EVENTS ============
        this.repoLoadList.addEventListener('click', () => this.renderRepoList());
        this.repoListType.addEventListener('change', () => this.renderRepoList());
        this.repoMediaType.addEventListener('change', () => this.renderRepoList());
    }

    toggleFullscreen() {
        if (!document.fullscreenElement) {
            this.videoContainer.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }

    toggleTheme() {
        document.body.classList.toggle('dark');
        this.themeToggle.textContent = document.body.classList.contains('dark') ? '☀️' : '🌙';
        localStorage.setItem('theme', document.body.classList.contains('dark') ? 'dark' : 'light');
    }

    toggleFavorite(url) {
        if (this.favorites.has(url)) {
            this.favorites.delete(url);
        } else {
            this.favorites.add(url);
        }
        localStorage.setItem('favorites', JSON.stringify([...this.favorites]));
        this.displayChannels(this.searchInput.value);
    }

    loadFavorites() {
        const saved = localStorage.getItem('favorites');
        if (saved) this.favorites = new Set(JSON.parse(saved));
        const theme = localStorage.getItem('theme');
        if (theme === 'dark') {
            document.body.classList.add('dark');
            this.themeToggle.textContent = '☀️';
        }
    }

    // ============================================================
    // Upload history
    // ============================================================
    loadUploadHistory() {
        const savedHistory = localStorage.getItem('uploadHistory');
        const savedPlaylists = localStorage.getItem('uploadedPlaylists');
        if (savedHistory) this.uploadHistory = JSON.parse(savedHistory);
        if (savedPlaylists) this.uploadedPlaylists = JSON.parse(savedPlaylists);
        this.displayUploadHistory();
    }

    addToUploadHistory(entry, channels = null) {
        const entryStr = `${new Date().toLocaleString()} - ${entry}`;
        if (!this.uploadHistory.some(item => item.includes(entry))) {
            this.uploadHistory.unshift(entryStr);
            if (this.uploadHistory.length > 5) this.uploadHistory.pop();
            if (channels) this.uploadedPlaylists[entry] = channels;
            localStorage.setItem('uploadHistory', JSON.stringify(this.uploadHistory));
            localStorage.setItem('uploadedPlaylists', JSON.stringify(this.uploadedPlaylists));
            this.displayUploadHistory();
        }
    }

    displayUploadHistory() {
        this.uploadHistoryContainer.innerHTML = this.uploadHistory.map(item => {
            const [time, entry] = item.split(' - ');
            return `<div class="upload-history-item" onclick="document.ownerspluginsTV.loadFromHistory('${entry}')">${item}</div>`;
        }).join('');
    }

    async loadFromHistory(entry) {
        this.showNotification(`Loading ${entry}...`);
        if (entry.startsWith('repo:')) {
            // format: repo:{media}/{list}/{id}
            const [, spec] = entry.split('repo:');
            const [mediaType, listType, id] = spec.split('/');
            this.uploadModal.classList.remove('show');
            await this.loadRepoChannels(mediaType, listType, id === 'all' ? null : id);
            return;
        }
        if (entry.match(/^https?:\/\/.+/)) {
            await this.fetchM3U(entry);
            this.uploadModal.classList.remove('show');
            if (this.channels.length > 0) this.playChannel(this.channels[0].url);
        } else if (this.uploadedPlaylists[entry]) {
            this.channels = this.uploadedPlaylists[entry];
            this.displayChannels();
            this.updatePlaylistStats();
            this.lastPlaylist = { type: 'file', value: entry };
            localStorage.setItem('lastPlaylist', JSON.stringify(this.lastPlaylist));
            this.uploadModal.classList.remove('show');
            this.showNotification(`Loaded ${entry} from history!`);
            if (this.channels.length > 0) this.playChannel(this.channels[0].url);
        } else {
            this.showNotification('Playlist data not found. Please re-upload the file.');
            this.fileUpload.value = '';
            this.fileUpload.click();
        }
    }

    // ============================================================
    // File / URL upload
    // ============================================================
    async handleFileUpload() {
        if (this.isUploading) return;
        const file = this.fileUpload.files[0];
        if (!file) return this.showNotification('Please select a file');

        this.isUploading = true;
        this.uploadFileButton.disabled = true;
        this.showNotification('Uploading file...');

        const reader = new FileReader();
        reader.onload = async (e) => {
            const data = e.target.result;
            if (file.name.endsWith('.m3u')) {
                this.channels = this.removeDuplicates(this.parseM3U(data));
            } else if (file.name.endsWith('.json')) {
                this.channels = this.removeDuplicates(this.parseJSON(data));
            } else if (file.name.endsWith('.txt')) {
                this.channels = this.removeDuplicates(this.parseTXT(data));
            } else {
                this.showNotification('Unsupported file format');
                this.isUploading = false;
                this.uploadFileButton.disabled = false;
                return;
            }
            this.displayChannels();
            this.updatePlaylistStats();
            this.addToUploadHistory(file.name, this.channels);
            this.lastPlaylist = { type: 'file', value: file.name };
            localStorage.setItem('lastPlaylist', JSON.stringify(this.lastPlaylist));
            this.uploadModal.classList.remove('show');
            this.showNotification('File uploaded successfully!');
            if (this.channels.length > 0) this.playChannel(this.channels[0].url);
            this.isUploading = false;
            this.uploadFileButton.disabled = false;
        };
        reader.onerror = () => {
            this.showNotification('Failed to read file');
            this.isUploading = false;
            this.uploadFileButton.disabled = false;
        };
        reader.readAsText(file);
    }

    async handleUrlUpload() {
        if (this.isUploading) return;
        const url = this.urlUpload.value.trim();
        if (!url) return this.showNotification('Please enter a URL');
        if (!url.match(/^https?:\/\/.+/)) return this.showNotification('Invalid URL format');

        this.isUploading = true;
        this.uploadUrlButton.disabled = true;
        this.showNotification('Loading URL...');

        try {
            const normalizedUrl = this.normalizeUrl(url);
            const response = await fetch(normalizedUrl, { cache: 'no-store' });
            if (!response.ok) throw new Error(`Fetch failed: ${response.status}`);
            const data = await response.text();
            if (url.endsWith('.m3u')) {
                this.channels = this.removeDuplicates(this.parseM3U(data));
            } else if (url.endsWith('.json')) {
                this.channels = this.removeDuplicates(this.parseJSON(data));
            } else if (url.endsWith('.txt')) {
                this.channels = this.removeDuplicates(this.parseTXT(data));
            } else {
                this.showNotification('Unsupported URL format');
                this.isUploading = false;
                this.uploadUrlButton.disabled = false;
                return;
            }
            this.displayChannels();
            this.updatePlaylistStats();
            this.addToUploadHistory(url);
            this.lastPlaylist = { type: 'url', value: url };
            localStorage.setItem('lastPlaylist', JSON.stringify(this.lastPlaylist));
            this.uploadModal.classList.remove('show');
            this.showNotification('URL loaded successfully!');
            if (this.channels.length > 0) this.playChannel(this.channels[0].url);
        } catch (error) {
            console.error('URL upload failed:', error);
            this.showNotification('Failed to load URL. Ensure it uses HTTPS.');
        } finally {
            this.isUploading = false;
            this.uploadUrlButton.disabled = false;
        }
    }

    // ============================================================
    // REPO browser (OwnerPlugins/famelack-data)
    // ============================================================
    async fetchRepoCategories(mediaType) {
        const cacheKey = `categories_${mediaType}`;
        if (this.repoCache[cacheKey]) return this.repoCache[cacheKey];

        const url = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${mediaType}/raw/categories`;
        const resp = await fetch(url, { cache: 'no-store' });
        if (!resp.ok) throw new Error(`GitHub API: HTTP ${resp.status}`);
        const items = await resp.json();

        const cats = items
            .filter(i => i && typeof i.name === 'string' && i.name.endsWith('.json'))
            .map(i => {
                const id = i.name.replace('.json', '');
                const name = id.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                return { id, name };
            })
            .sort((a, b) =>
                (a.id !== 'all') - (b.id !== 'all') || a.name.localeCompare(b.name)
            );

        this.repoCache[cacheKey] = cats;
        return cats;
    }

    async fetchRepoCountries(mediaType) {
        const cacheKey = `countries_${mediaType}`;
        if (this.repoCache[cacheKey]) return this.repoCache[cacheKey];

        const url = `${repoBase()}/${mediaType}/raw/countries_metadata.json`;
        const resp = await fetch(url, { cache: 'no-store' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        const items = Object.entries(data || {})
            .filter(([, info]) => info && info.hasChannels)
            .map(([code, info]) => ({
                id: code,
                name: info.country || code.toUpperCase(),
                count: info.channelCount || 0
            }))
            .sort((a, b) => a.name.localeCompare(b.name));

        this.repoCache[cacheKey] = items;
        return items;
    }

    async renderRepoList() {
        const mediaType = this.repoMediaType.value;
        const listType = this.repoListType.value;
        const container = this.repoListContainer;

        container.innerHTML = '<p class="repo-hint">Loading...</p>';

        try {
            if (listType === 'all') {
                container.innerHTML = '';
                const btn = document.createElement('button');
                btn.className = 'repo-btn repo-btn-block';
                btn.textContent = `Load ALL ${mediaType.toUpperCase()} channels`;
                btn.onclick = () => this.loadRepoChannels(mediaType, 'all', null);
                container.appendChild(btn);
                return;
            }

            let items;
            if (listType === 'categories') {
                items = await this.fetchRepoCategories(mediaType);
            } else {
                items = await this.fetchRepoCountries(mediaType);
            }

            if (items.length === 0) {
                container.innerHTML = '<p class="repo-hint">No items found.</p>';
                return;
            }

            container.innerHTML = '';
            items.forEach(item => {
                const row = document.createElement('div');
                row.className = 'repo-item';
                const label = document.createElement('span');
                label.className = 'repo-item-name';
                label.textContent = item.name;
                row.appendChild(label);
                if (item.count !== undefined) {
                    const count = document.createElement('span');
                    count.className = 'repo-item-count';
                    count.textContent = `${item.count}`;
                    row.appendChild(count);
                }
                row.onclick = () => this.loadRepoChannels(mediaType, listType, item.id);
                container.appendChild(row);
            });
        } catch (e) {
            container.innerHTML = `<p class="repo-error">Error: ${e.message}</p>`;
        }
    }

    async loadRepoChannels(mediaType, listType, id, silent = false) {
        if (!silent) this.showNotification(`Loading ${mediaType}/${listType}${id ? '/' + id : ''}...`);
        try {
            let url;
            if (listType === 'all') {
                url = `${repoBase()}/${mediaType}/raw/categories/all.json`;
            } else if (listType === 'categories') {
                url = `${repoBase()}/${mediaType}/raw/categories/${id}.json`;
            } else if (listType === 'countries') {
                url = `${repoBase()}/${mediaType}/raw/countries/${String(id).toLowerCase()}.json`;
            } else {
                throw new Error('Unknown list type');
            }

            const resp = await fetch(url, { cache: 'no-store' });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();

            const list = parseFamelackPayload(data, listType === 'countries' ? id : null);
            const channels = list
                .map((item, i) => this.toOwnersChannel(item, i, mediaType))
                .filter(Boolean);

            if (channels.length === 0) {
                if (!silent) this.showNotification('No playable channels found in this list');
                return;
            }

            this.channels = this.removeDuplicates(channels.sort((a, b) =>
                a.group === b.group ? a.title.localeCompare(b.title) : a.group.localeCompare(b.group)
            ));

            this.displayChannels();
            this.updatePlaylistStats();

            const tag = `repo:${mediaType}/${listType}/${id || 'all'}`;
            this.addToUploadHistory(tag);
            this.lastPlaylist = { type: 'repo', value: `${mediaType}/${listType}/${id || 'all'}` };
            localStorage.setItem('lastPlaylist', JSON.stringify(this.lastPlaylist));

            if (!silent) {
                this.uploadModal.classList.remove('show');
                this.showNotification(`Loaded ${this.channels.length} channels`);
                if (this.channels.length > 0) this.playChannel(this.channels[0].url);
            }
        } catch (e) {
            console.error('Repo load failed:', e);
            if (!silent) this.showNotification(`Repo load failed: ${e.message}`);
        }
    }

    // ============================================================
    // Misc
    // ============================================================
    clearHistory() {
        this.channels = [];
        this.channelGroups = {};
        this.currentChannel = null;
        this.epgData = [];
        this.favorites.clear();
        this.uploadHistory = [];
        this.lastPlaylist = null;
        this.uploadedPlaylists = {};
        this.filterStatus = null;
        this.repoCache = {};
        localStorage.removeItem('favorites');
        localStorage.removeItem('uploadHistory');
        localStorage.removeItem('lastPlaylist');
        localStorage.removeItem('uploadedPlaylists');
        this.displayChannels();
        this.updatePlaylistStats();
        this.displayUploadHistory();
        this.repoListContainer.innerHTML = '<p class="repo-hint">Choose Media + List, then press "Load List".</p>';
        this.cleanupPlayer();
        this.updateEPGDisplay({ programs: [] });
        this.showNotification('History cleared!');
        this.updatePlayerSize();
    }

    updateChannelSelection() {
        this.displayChannels(this.searchInput.value);
    }

    handleError(error, message) {
        console.error(`${message}:`, error);
        this.loadingIndicator.classList.remove('show');
        let detailedMessage = message;
        if (error?.type === Hls.ErrorTypes.NETWORK_ERROR) {
            detailedMessage = 'Network error: Stream may be offline or blocked.';
        } else if (error?.type === Hls.ErrorTypes.MEDIA_ERROR) {
            detailedMessage = 'Media error: Stream format may not be supported.';
        } else if (error?.code === MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED) {
            detailedMessage = 'This stream is not supported by your browser.';
        }
        this.showNotification(`${detailedMessage} Trying next channel...`);

        const currentIndex = this.channels.findIndex(c => c.url === this.currentChannel?.url);
        const nextChannel = this.channels.slice(currentIndex + 1).find(c => c.status === 'active');
        if (nextChannel) {
            this.playChannel(nextChannel.url);
        } else {
            this.showNotification('No more active channels available.');
        }
    }

    showNotification(message) {
        this.notification.textContent = message;
        this.notification.classList.add('show');
        setTimeout(() => this.notification.classList.remove('show'), 3000);
    }

    registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/service-worker.js')
                    .then(reg => console.log('Service Worker registered:', reg))
                    .catch(err => console.error('Service Worker registration failed:', err));
            });
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.ownerspluginsTV = new OwnersPluginsTV();
});