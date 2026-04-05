# OpenRaven Chrome Extension — Privacy Policy

**Last updated:** 2026-04-05

## What data does this extension access?

When you click "Save to Knowledge Base" or use the context menu, the extension reads the text content of the current web page (or your selected text) and sends it to your configured OpenRaven server.

## Where does the data go?

Your data is sent **only** to the OpenRaven server URL you configure in the extension settings. By default, this is `http://localhost:3002` (your local machine). No data is ever sent to third-party servers, analytics services, or the extension developer.

## What permissions does the extension use?

- **activeTab / scripting**: Read the current page's text content when you click Save
- **cookies**: Read your OpenRaven session cookie for authenticated cloud mode
- **contextMenus**: Add "Save to OpenRaven" to the right-click menu
- **storage**: Save your settings (API URL, auth mode) across browser sessions
- **host_permissions (<all_urls>)**: Required to connect to your configurable OpenRaven server URL

## Data storage

The extension stores only your settings (API URL and auth mode) using Chrome's sync storage. No page content is stored locally by the extension.

## Contact

For questions about this privacy policy, please open an issue at:
https://github.com/chesterkuo/OpenRaven/issues
