[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyInvest

*Un espace public multilingue pour des notes datees sur les actions, les secteurs et les societes americaines de croissance encore peu suivies.*

[![Website](https://img.shields.io/badge/Website-earn.lazying.art-0EA5E9?style=for-the-badge)](https://earn.lazying.art)
[![Research](https://img.shields.io/badge/Research-Markdown-111827?style=for-the-badge&logo=markdown&logoColor=white)](../US_Sector_Investment_Matrix_2026-06-13.md)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-lachlanchen-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/lachlanchen)

LazyInvest rassemble des notes de recherche qui distinguent la force actuelle des secteurs, les themes deja tres populaires, les candidats de croissance moins visibles, les paris speculatifs et les societes a eviter. Le depot est concu pour etre mis a jour facilement: chaque note est datee, sourcee et ecrite en Markdown.

Ce depot est un carnet de recherche, pas un conseil financier personnalise. Les prix, la guidance, les lois, les taux et les nouvelles peuvent changer rapidement; verifiez les sources primaires avant d'utiliser une note.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## Contenu Actuel

| Fichier | Role |
|---|---|
| [US_Sector_Investment_Matrix_2026-06-13.md](../US_Sector_Investment_Matrix_2026-06-13.md) | Tableau sectoriel maintenu: meilleurs themes actuels, themes chauds, idees moins suivies, risques eleves et valeurs a eviter. |
| [US_Underfollowed_Growth_Stocks_2026-06-13.md](../US_Underfollowed_Growth_Stocks_2026-06-13.md) | Liste ciblee de societes americaines de croissance moins visibles, avec catalyseurs et risques. |
| [AGENTS.md](../AGENTS.md) | Regles locales pour les futures mises a jour de recherche. |

## Demarrage Rapide

```bash
git clone https://github.com/lachlanchen/LazyInvest.git
cd LazyInvest
ls
```

Ouvrez les fichiers Markdown directement sur GitHub ou avec n'importe quel lecteur Markdown.

## Flux de Mise a Jour

1. Choisir une note datee.
2. Actualiser les sources primaires: relations investisseurs, documents SEC, transcriptions, donnees boursieres et donnees de marche fiables.
3. Conserver la distinction entre GAAP et non-GAAP.
4. Mettre a jour les hypotheses, les liens et la date de recherche.

## Validation

```bash
rg -n "CITATION\\.cff|Source:|not personal financial advice" ../README.md . ../*.md
git diff --check
```

## Citation

Si vous utilisez LazyInvest dans une recherche, citez le depot. GitHub lit [CITATION.cff](../CITATION.cff) et affiche le panneau **Cite this repository** sur la page du depot.

```bibtex
@software{chen_lazyinvest_2026,
  author = {Chen, Lachlan},
  title = {LazyInvest: Dated U.S. Sector and Stock Research Notes},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyInvest}
}
```

## Statut

Premiere publication publique: 2026-06-13. Les premieres notes couvrent les secteurs americains, les entreprises de croissance moins suivies, les themes chauds, les paris speculatifs et les candidats a eviter.
