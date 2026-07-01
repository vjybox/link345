# Putting The Lithium Index on Blogger

## Why a raw paste shows an empty box

Blogger **Pages and Posts strip `<script>`, `<input>`, `<select>` and
`<button>`** for security. This directory is a JavaScript app, so on a Page
its code never runs and its search/filter controls are deleted — you get the
styled grid background with nothing inside it. This is a Blogger limitation,
not a bug in the build; **a Blogger Page cannot run the app directly.**

There are only two dependable ways to run it:

---

## ✅ Recommended: host it + embed with an `<iframe>`

The app runs on GitHub Pages (where scripts work); your Blogger Page just
frames it. `<iframe>` is allowed on Blogger Pages (same mechanism as a YouTube
or Google Maps embed), and GitHub Pages permits framing.

### 1. Turn on GitHub Pages (one time, ~15 seconds)

Repo **vjybox/link345** → **Settings → Pages** →
**Build and deployment → Source: “Deploy from a branch”** →
**Branch:** `main` **/** `(root)` → **Save**.

*(If `main` doesn’t yet contain `index.html`, either merge the PR first, or
just pick the `claude/lithium-index-directory-n9a7c0` branch instead — both
serve the same file.)*

After ~1 minute the app is live at:

```
https://vjybox.github.io/link345/
```

Open that URL directly to confirm it works (search, filters, cards).

### 2. Put the iframe on your Blogger Page

Blogger → your page → **HTML view** → replace the body with:

```html
<iframe
  src="https://vjybox.github.io/link345/"
  title="The Lithium Index"
  loading="lazy"
  style="width:100%; height:900px; border:1px solid #e4e4e4; display:block;">
</iframe>
```

Publish. The directory scrolls inside the frame; its sticky header stays put.
Adjust `height` to taste (e.g. `1100px`).

---

## Alternative: HTML/JavaScript gadget (no hosting)

If you’d rather not host, scripts *are* allowed in a gadget (just not in a
Page body):

Blogger → **Layout → Add a Gadget → HTML/JavaScript** → paste the entire
contents of **`blogger-embed.html`** → Save.

Downside: a gadget lives in a layout region (sidebar/footer/below-posts),
not as a standalone page body, so it’s better for embedding alongside content
than as a dedicated homepage. For a full-page homepage, use the iframe route.
