# Owners Plugins - Professional Streaming App

![Owners Plugins Logo](./img/logo.png)

Owners Plugins is a Progressive Web App (PWA) designed to stream your favorite TV channels using custom playlists in M3U, JSON, or TXT formats. With a sleek, responsive UI, pastel dark/light themes, and features like built-in repository browsing, EPG display, and channel filtering, it offers a professional streaming experience directly from your browser or as an installable app.

---

## Features

- **Playlist Support**: Upload M3U, JSON, or TXT playlists via file or URL.
- **Built-in Repository Browser**: Directly load channels, categories, and countries from the `OwnerPlugins/famelack-data` GitHub repository.
- **Channel Management**:
  - Automatic duplicate removal based on URL and title.
  - Filter channels by status (Total, Active, Offline) with clickable stats.
  - Search channels by name or group.
  - Favorite channels with persistent storage.
- **Streaming**: Supports HLS (`.m3u8`) via `hls.js` and native playback for other formats.
- **EPG**: Displays current and next programs with a progress bar (requires EPG data).
- **UI/UX**:
  - Responsive design with a collapsible sidebar.
  - Modern Pastel Light and Deep Dark themes with toggle.
  - Fullscreen video mode.
  - Custom logo in the header.
- **PWA**: Installable on desktop/mobile, with offline caching for core assets.
- **Local Storage**: Persists favorites, upload history, and last playlist.
- **Notifications**: Welcome message with disclaimer, plus status updates.

---

## Screenshots

![Main Interface](./screenshots/entry.png?text=Main+Interface)
![Player Light](./screenshots/player-light.png?text=Player+Light)
![Player dark](./screenshots/player-dark.png?text=Player+Dark)

---

## Prerequisites

- A modern web browser (Chrome, Firefox, Safari, etc.).
- HTTPS hosting for PWA features (e.g., GitHub Pages, Netlify, Vercel).
- A valid M3U, JSON, or TXT playlist file/URL.

---

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/owners-plugins.git
   cd owners-plugins
   ```

2. **Run Locally**:
   Since Service Workers require a secure context, run a local server:
   ```bash
   python -m http.server 8000
   ```
   Open `http://localhost:8000` in your browser.

---

## How to Use

1. Open the app.
2. Click the **Menu (☰)** button or the **Upload** modal will appear on first load.
3. Choose one of the following methods:
   - **Upload File**: Select a local `.m3u`, `.json`, or `.txt` file.
   - **Load URL**: Paste a direct link to a playlist.
   - **Repo Browser**: Select `TV` or `Webcams`, choose `Categories`, `Countries`, or `All Channels`, and click **Load List**.
4. Select a channel from the sidebar to start streaming.

---

## Dependencies

- [HLS.js](https://github.com/video-dev/hls.js/) (v1.5.13) - Loaded via CDN for HLS streaming.
- [Google Fonts](https://fonts.google.com/) (Inter, Playfair Display) - For typography.
- No additional installations are required beyond the included files.

---

## Development

To customize or extend Owners Plugins:
- **Edit Styles**: Modify `css/styles.css` for UI changes.
- **Add Features**: Update `js/script.js` (e.g., new playlist formats, UI enhancements).
- **Test Locally**: Use a local server and browser DevTools.

---

## Disclaimer

Owners Plugins is a media player interface. It does not host, provide, or distribute any media content, streams, or playlists. The user is solely responsible for the content accessed through this software. Owners Plugins does not verify the legality or quality of the streams provided by third-party sources (such as uploaded M3U lists or external repositories). Users must ensure they have the legal right to access any content they stream.

---

## Contributing

- Fork the repository.
- Create a feature branch (`git checkout -b feature-name`).
- Commit changes (`git commit -m "Add feature"`).
- Push to the branch (`git push origin feature-name`).
- Open a Pull Request.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
