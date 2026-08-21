# AdSense setup — do this AFTER approval

Nothing here should be added to the site before the account is approved.
Empty `<ins>` blocks render as blank space and count as a
"made for advertising" signal during review. Nine of them were removed from
`index.html` in commit `56ea4e6` for exactly that reason.

The `adsbygoogle.js` tag is already in the `<head>` of all 26 pages. That is
the whole requirement for review.

---

## Option A — Auto ads (recommended, no code)

1. AdSense → **Ads** → **By site** → `worldpulse.fyi` → **Edit**
2. Turn **Auto ads** on
3. Set **Ad load** to about 50–60% to start, not maximum
4. Turn **off** "Anchor ads" and "Vignette ads" on mobile initially — they are
   the formats most likely to annoy people into leaving, and this site's value
   is a live counter people watch for a while
5. Save. Ads appear within roughly an hour.

No files change. Google chooses placements itself.

---

## Option B — Manual units (more control, needs code)

Only worth doing once there is enough traffic to compare placements.

### 1. Create the unit

AdSense → **Ads** → **By ad unit** → **Display ads** → name it (e.g.
`wp-in-article-1`) → **Responsive** → **Create**. Copy the `data-ad-slot`
number it gives you.

### 2. Paste this where the ad should sit

```html
<div class="ad-slot-inline">
  <ins class="adsbygoogle"
       style="display:block"
       data-ad-client="ca-pub-1766368165161679"
       data-ad-slot="PASTE_SLOT_ID_HERE"
       data-ad-format="auto"
       data-full-width-responsive="true"></ins>
  <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>
```

### 3. Add this CSS once, to the shared `<style>` block

Reserves height so the page does not jump when the ad loads. Layout shift
hurts Core Web Vitals, which feeds back into search ranking.

```css
.ad-slot-inline {
  min-height: 280px;
  margin: 28px 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.ad-slot-inline::before {
  content: "Advertisement";
  position: absolute;
  font-size: 11px;
  letter-spacing: .06em;
  text-transform: uppercase;
  color: var(--muted);
  opacity: .5;
}
@media (max-width: 600px) { .ad-slot-inline { min-height: 250px; } }
```

The "Advertisement" label is required by AdSense policy if an ad could be
mistaken for site content. It sits behind the ad and is covered once one loads.

---

## Where to put them on this site

Keep it to **two per article, three maximum**. Content-to-ad ratio is a live
policy, and this site's articles are 600–750 words, which is not a lot of room.

| Placement | Where | Notes |
|---|---|---|
| In-article 1 | After the 2nd or 3rd `<p>` of `<main>` | Best earner on long pages |
| In-article 2 | Before the final `<h2>` | Only on 600+ word pages |
| Below content | Just above `.related` | Safe, low complaint rate |

Do **not** place ads:

- Anywhere in the hero on `index.html` — it would sit on top of the globe and
  the live counter, which is the reason people come
- Inside or above the `.header` nav
- On `globe-hd.html` — it is a `noindex` iframe payload, not a page
- On `404.html`, `privacy.html`, or `terms.html` — low value, and ads on error
  and legal pages read badly

---

## After ads are live

- Watch **Page RPM** per page in AdSense, not just total revenue
- Compare against bounce rate in GA4 (`G-Q762BNE94L`). If bounce climbs sharply
  after enabling a format, that format is costing more in lost visits than it earns
- The consent banner already gates ad personalisation via Consent Mode v2, so
  EU traffic is handled — no change needed there

---

## What Cloudflare actually offers

There is no Cloudflare ad network. Their publisher product is **Pay Per Crawl**,
which charges AI companies for crawling your content — a different thing
entirely, in private beta, and aimed at publishers with content AI firms want to
license.

**Considered and deliberately declined, Aug 2026.** Cloudflare is not in this
site's path at all: nameservers are Porkbun, the site is served directly by
GitHub Pages (no `cf-ray` header), and MX points at ImprovMX. Pay Per Crawl runs
at Cloudflare's proxy layer, so adopting it means migrating DNS wholesale —
re-creating 4 GitHub Pages A records and 2 ImprovMX MX records, enabling
proxying, and setting SSL to *Full* (Flexible causes a redirect loop with GitHub
Pages).

Reasons against, at this stage:

- Breaking the MX records kills `contact@worldpulse.fyi`, which AdSense requires
- A crawler-control layer works against the current priority, which is getting
  the 14 unindexed pages crawled
- Up to 48h propagation downtime mid-application
- The content is derived from public World Bank and UN data, so there is nothing
  proprietary for an AI company to license
- Private beta: acceptance is not guaranteed

Worth revisiting only after AdSense approval, and only if the site develops
genuinely original data worth licensing.

If AdSense keeps failing, the realistic alternatives that accept smaller sites
are **Ezoic** (accepts low traffic, Google-certified partner, approves in days)
and **Media.net**. Both can run instead of, or alongside, AdSense.
