---
name: fable5-websites-prompt
description: "A Claude Fable 5 prompt template for building 5 fundamentally different showcase websites — self-contained HTML, 3D scenes, particle systems, animations, Vercel deploy. Use for creative web showcases, portfolio sites, Fable 5 demo sites, or high-end one-page HTML builds."
swarm-worker: innovator
model-hint: deepseek-v4-flash-free|nemotron-3-ultra-free
---

# Fable 5 — 5 Websites Prompt

A structured prompt template for Claude Fable 5 (or any coding model) to autonomously build 5 distinct high-end showcase websites.

## The Prompt

```
I'm building a small library of showcase websites to demonstrate Fable 5's design
and animation abilities, and to record a YouTube video walking through the results
and the exact prompt I used. The video is for Gulf business owners and creators
who want to see what one prompt can produce, so the sites need to look genuinely
high-end, not template-grade.

With that in mind: build 5 fundamentally different websites, each one a standalone
showcase of your own taste in web design. Make them different from each other on
every axis you can — layout, motion, color, typography, and interaction. Use
whatever advanced visual techniques you think best show your skill: 3D scenes,
particle systems, real-time shaders, unusual animations, expressive color
palettes, and distinctive fonts. I am deliberately not giving you a structure or
a step framework. You have better design taste than I do, so I want you to make
the creative decisions yourself. Get out of your own way and show what you can
actually do.

For source assets and inspiration, you have these instead of stock photo sites:
pull reference and inspiration from motion-design and award sites (for example
Awwwards, Godly, and similar galleries) and from component references like
21st.dev, then design something new in that spirit rather than copying. Generate
any images you need with the Codex image model, which you have access to. You
have total creative freedom — these references are a starting point, not a cage.

Build each website as ONE single, self-contained, high-quality HTML file: all CSS,
all JavaScript, all animation and 3D code inline in that one file, so I can copy
the whole file and drop it anywhere and it just works. No build step, no framework
project, no separate asset folders unless a file genuinely cannot be inlined.
Treat the quality bar as production, not demo: clean structure, smooth 60fps
motion, no console errors, responsive down to mobile.

As you finish each site, verify it yourself: open the HTML file in a real browser
using Chrome DevTools MCP, check that it renders, that the animations run, that
the console is clean, and that nothing is broken, and fix what you find. Do at
least 3 iteration passes per site: after a site works, go back through it looking
for design problems and chances to make it more refined and more interesting, and
improve it each pass.

Once a site passes its 3 iteration passes, deploy it live. Prefer Vercel; if
Vercel is not available in this environment, use Netlify. Deploy each one as its
own project and capture the live URL. If a deploy step needs an account login you
do not have, skip the deploy for that site, keep the finished HTML file, and tell
me which sites still need deploying rather than stopping.

Your goal: 5 finished, fundamentally different websites, each a single
self-contained HTML file, each verified in a browser, each taken through 3
iteration passes, and each deployed live (Vercel preferred, Netlify fallback).
Work completely autonomously and do not ask me for anything until all 5 are done.
When you finish, give me for each site: the local HTML file path, the live URL,
and a two-line note on what makes it different.
```

## Workflow

1. **Generate** — model builds 5 HTML files autonomously
2. **Verify** — open each in browser via DevTools MCP
3. **Iterate** — 3 refinement passes per site
4. **Deploy** — Vercel (preferred) or Netlify

## Similar Skills

- `prompt-engineering`, `prompt-engineering-patterns` — general prompt design
- `prompt-caching`, `prompt-library` — prompt management
- `enhance-prompt`, `llm-prompt-optimizer` — prompt optimisation
- `llm-application-dev-prompt-optimize` — LLM prompt optimisation
- `web-artifacts-builder` — building HTML artifacts
- `premium-3d-website` — 3D web showcase building
- `frontend-slides` — creative HTML presentations
