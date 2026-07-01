# Putting The Lithium Index on Blogger

Blogger **Pages/Posts strip `<script>`, `<input>`, `<select>`, `<button>` and
`<form>`** for security. They keep `<style>`, `<div>`, `<span>`, `<a>`,
headings and `<details>`/`<summary>`. That single fact decides which build to
use.

There are three options, from "works instantly" to "full app".

---

## Option A — `blogger-page.html`  (recommended for a Page; zero hosting)

A **no-JavaScript** directory built only from tags Blogger allows. It uses
native `<details>`/`<summary>` for the collapsible hierarchy, so it works the
moment you paste it — no hosting, no gadget, no setup.

**What you get:** the full 1,996-entry catalog, browsable as
20 mega-sectors → 146 categories → entry cards; live counts; verified ✓
links + web-search fallback; technology tags; a jump-to-sector menu.

**What a Page can't do (needs JavaScript):** the live search box, the
dropdown filters and pagination. Use the browser's **Ctrl/⌘ + F** to find
text, or use Option B to get the interactive search back.

**Steps**

1. Open `blogger-page.html`, copy the **entire** file.
2. Blogger → **New Page** (or Post) → switch the editor to **HTML view** →
   paste → **Publish**.
3. Optional: set it as your homepage in Settings.

> Keep the editor in **HTML view** the whole time. Toggling to *Compose* can
> make Blogger re-sanitize and mangle the markup — if that happens, clear the
> page and paste again in HTML view.

---

## Option B — iframe to the full interactive app  (adds search + filters)

Runs the complete `index.html` (search box, dropdown filters, pagination) on
GitHub Pages and frames it into your Blogger Page. `<iframe>` is allowed on
Pages (same as a YouTube embed).

1. **Enable GitHub Pages** (one time, ~15 s): repo **vjybox/link345** →
   **Settings → Pages → Source: “Deploy from a branch”** → branch `main`
   `/(root)` → **Save**. *(If `main` lacks `index.html`, merge the PR first or
   pick the `claude/lithium-index-directory-n9a7c0` branch.)* The app goes live
   at `https://vjybox.github.io/link345/`.
2. In your Blogger Page (**HTML view**) paste:

   ```html
   <iframe
     src="https://vjybox.github.io/link345/"
     title="The Lithium Index"
     loading="lazy"
     style="width:100%; height:900px; border:1px solid #e4e4e4; display:block;">
   </iframe>
   ```

Adjust `height` to taste. The app scrolls inside the frame.

---

## Option C — HTML/JavaScript gadget  (`blogger-embed.html`)

Scripts *are* allowed in a gadget (just not in a Page body), so the scoped
`blogger-embed.html` runs there with full search/filters.

Blogger → **Layout → Add a Gadget → HTML/JavaScript** → paste the entire
`blogger-embed.html` → **Save**. Best when you want the interactive widget
inside a layout region rather than as a standalone page.

---

## Enabling "Submit a company"

The header **＋ Submit** button and each drawer's "Suggest an edit" link open
whatever URL is set as `SUBMIT_URL` at the top of the `<script>` in
`build.py` (default is a placeholder). Create a Google Form or Tally form,
paste its URL into `SUBMIT_URL`, and re-run `python3 build.py`.

## Which should I pick?

| Want… | Use |
| --- | --- |
| A standalone directory page, no setup, right now | **A** (`blogger-page.html`) |
| Live search + filters as a full page | **B** (iframe, needs GitHub Pages) |
| Interactive widget in a sidebar/footer region | **C** (gadget, `blogger-embed.html`) |
