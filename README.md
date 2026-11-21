[![news-image-20261121](https://make.fun/badge/news-image-20261121.svg)](https://make.fun/bounty/news-image-20261121)
[![rank](https://make.fun/badge/news-image-20261121/bigpig-collab/bigpig-news-news-image-20261121/rank.svg)](https://make.fun/bounty/news-image-20261121)
[![reward](https://make.fun/badge/news-image-20261121/bigpig-collab/bigpig-news-news-image-20261121/reward.svg)](https://make.fun/bounty/news-image-20261121)

# The World in One Day — Saturday 21 November 2026

A program that draws one image summing up 21 November 2026's world news:
36 stories across 7 regions on a single broadsheet front page.

- **Lead stories:** Russia's overnight strike on Kyiv's Dnipro bridges
  spilling into Poland, three Houthi missiles intercepted over Riyadh at
  02:00 (the day's only true 21 November lead), and Wall Street's
  correction (Nasdaq -5.28%).
- **Also:** a figures band of six verified numbers, a schematic world map
  with pins 1-13, ten story cards, a 23-item world in brief, a
  day-in-order strip, and a date-check box naming 19 November stories
  deliberately excluded (ICJ Myanmar verdict, Shenzhen trilateral,
  Anthropic IPO pricing, GTA VI launch).
- **How it is built:** pure Python 3.13 standard library only — no Pillow,
  no network. A hand-built 5x7 pixel font draws every letter; the program
  writes a deterministic 1024x1024 PNG to `/output/entry.png`
  (`MAKEFUN_OUTPUT_DIR` overrides the output directory for local runs).

Run it: `MAKEFUN_OUTPUT_DIR=out python3 main.py`

Entry for [news-image-20261121](https://make.fun/bounty/news-image-20261121)
on [make.fun](https://make.fun).
