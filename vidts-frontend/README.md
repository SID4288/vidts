# vidts Frontend — Minimal File Placement

This is a **plain JavaScript React frontend**. The application has no TypeScript source files and no application backend. The small `server/index.js` file only serves the built React files when the managed project is published.

| Place | Keep this file | Purpose |
| --- | --- | --- |
| Project root | `package.json` | Defines the React dependencies and the development/build commands. |
| Project root | `vite.config.js` | Tells Vite that the application lives in `client/` and supports the managed image paths. |
| `client/` | `index.html` | The single HTML page containing the React mount point. |
| `client/src/` | `main.jsx` | Starts React and loads global styling. |
| `client/src/` | `App.jsx` | The top-level React component. |
| `client/src/pages/` | `Home.jsx` | The complete public document-to-video interface. |
| `client/src/` | `index.css` | All global styles, responsive rules, and the hourglass animation. |
| `server/` | `index.js` | Managed-hosting static file server; it does not implement document conversion or authentication. |

## Where to add future code

Add another visible screen in `client/src/pages/`. Add reusable React pieces, such as a document preview or a video card, in `client/src/components/` only when they are used in more than one page. Put ordinary images in the managed storage service and reference their `/manus-storage/...` URL; do not put large images or videos inside `client/public/`.

> The current upload, sign-in choices, hourglass, and finished-video view are frontend states. Real document upload, Google/Facebook/email sign-in, and video creation need a backend service before they can process user data.
