[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyInvest

*Ein mehrsprachiger offener Arbeitsbereich fuer datierte Recherchen zu US-Aktien, Sektoren und wenig beachteten Wachstumsunternehmen.*

[![Website](https://img.shields.io/badge/Website-earn.lazying.art-0EA5E9?style=for-the-badge)](https://earn.lazying.art)
[![Research](https://img.shields.io/badge/Research-Markdown-111827?style=for-the-badge&logo=markdown&logoColor=white)](../US_Sector_Investment_Matrix_2026-06-13.md)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-lachlanchen-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/lachlanchen)

LazyInvest sammelt Research-Notizen, die aktuelle Sektorstaerke, ueberlaufene Momentum-Themen, weniger beachtete Wachstumswerte, spekulative Chancen und Unternehmen auf der Meiden-Liste trennen. Das Repository ist leicht aktualisierbar: jede Notiz ist datiert, verlinkt Quellen und nutzt Markdown.

Dies ist ein Research-Notizbuch, keine persoenliche Finanzberatung. Marktpreise, Unternehmensprognosen, Gesetze, Zinssaetze und Nachrichten aendern sich schnell; pruefen Sie primaere Quellen vor jeder Nutzung.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## Aktueller Inhalt

| Datei | Zweck |
|---|---|
| [US_Sector_Investment_Matrix_2026-06-13.md](../US_Sector_Investment_Matrix_2026-06-13.md) | Gepflegte Sektortabelle mit besten aktuellen Ideen, heissen Themen, wenig beachteten Kandidaten, Risiken und Meiden-Liste. |
| [US_Underfollowed_Growth_Stocks_2026-06-13.md](../US_Underfollowed_Growth_Stocks_2026-06-13.md) | Fokussierte Watchlist weniger beachteter US-Wachstumsunternehmen mit Katalysatoren und Risiken. |
| [AGENTS.md](../AGENTS.md) | Lokale Arbeitsregeln fuer kuenftige Research-Updates. |

## Schnellstart

```bash
git clone https://github.com/lachlanchen/LazyInvest.git
cd LazyInvest
ls
```

Oeffnen Sie die Markdown-Dateien direkt auf GitHub oder mit einem beliebigen Markdown-Viewer.

## Aktualisierung

1. Eine datierte Notiz auswaehlen.
2. Primaerquellen aktualisieren: Investor Relations, SEC-Filings, Transkripte, Boersendaten und serioese Marktdaten.
3. GAAP und Non-GAAP sauber trennen.
4. Annahmen, Links und Research-Datum aktualisieren.

## Validierung

```bash
rg -n "CITATION\\.cff|Source:|not personal financial advice" ../README.md . ../*.md
git diff --check
```

## Zitation

Wenn Sie LazyInvest in einer Recherche verwenden, zitieren Sie das Repository. GitHub liest [CITATION.cff](../CITATION.cff) und zeigt auf der Repository-Seite den Bereich **Cite this repository** an.

```bibtex
@software{chen_lazyinvest_2026,
  author = {Chen, Lachlan},
  title = {LazyInvest: Dated U.S. Sector and Stock Research Notes},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyInvest}
}
```

## Status

Erste oeffentliche Version: 2026-06-13. Die ersten Notizen behandeln US-Sektoren, weniger beachtete Wachstumswerte, heisse Themen, spekulative Chancen und Unternehmen zum Meiden.
