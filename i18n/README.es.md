[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyInvest

*Un espacio publico multilingue para investigacion fechada sobre acciones, sectores y empresas estadounidenses de crecimiento poco seguidas.*

[![Website](https://img.shields.io/badge/Website-earn.lazying.art-0EA5E9?style=for-the-badge)](https://earn.lazying.art)
[![Research](https://img.shields.io/badge/Research-Markdown-111827?style=for-the-badge&logo=markdown&logoColor=white)](../US_Sector_Investment_Matrix_2026-06-13.md)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-lachlanchen-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/lachlanchen)

LazyInvest reune notas de investigacion que separan fortaleza sectorial actual, impulso de mercado ya concurrido, candidatos de crecimiento menos visibles, apuestas especulativas y empresas que conviene evitar. El repositorio esta pensado para actualizarse con facilidad: cada nota tiene fecha, enlaces a fuentes y formato Markdown.

Esto es un cuaderno de investigacion, no asesoramiento financiero personal. Los datos de mercado, las guias de las empresas, las leyes, las tasas y las noticias cambian rapido; revise fuentes primarias antes de usar cualquier nota.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## Contenido Actual

| Archivo | Proposito |
|---|---|
| [US_Sector_Investment_Matrix_2026-06-13.md](../US_Sector_Investment_Matrix_2026-06-13.md) | Tabla mantenida por sector: mejores ideas actuales, temas calientes, empresas menos seguidas, lista de riesgo y lista de evitar. |
| [US_Underfollowed_Growth_Stocks_2026-06-13.md](../US_Underfollowed_Growth_Stocks_2026-06-13.md) | Lista enfocada de empresas estadounidenses de crecimiento menos visibles, con catalizadores y riesgos. |
| [AGENTS.md](../AGENTS.md) | Reglas locales para futuras actualizaciones de investigacion. |

## Inicio Rapido

```bash
git clone https://github.com/lachlanchen/LazyInvest.git
cd LazyInvest
ls
```

Abra los archivos Markdown directamente en GitHub o con cualquier visor Markdown.

## Flujo de Actualizacion

1. Elija una nota fechada para actualizar.
2. Actualice fuentes primarias: relaciones con inversores, documentos SEC, transcripciones, datos de bolsa y datos de mercado reputados.
3. Mantenga separadas las metricas GAAP y no GAAP.
4. Actualice supuestos, enlaces y fecha de investigacion.

## Validacion

```bash
rg -n "CITATION\\.cff|Source:|not personal financial advice" ../README.md . ../*.md
git diff --check
```

## Citacion

Si usa LazyInvest en investigacion, cite el repositorio. GitHub lee [CITATION.cff](../CITATION.cff) y muestra el panel **Cite this repository** en la pagina del repositorio.

```bibtex
@software{chen_lazyinvest_2026,
  author = {Chen, Lachlan},
  title = {LazyInvest: Dated U.S. Sector and Stock Research Notes},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyInvest}
}
```

## Estado

Primera publicacion publica: 2026-06-13. Las primeras notas cubren sectores estadounidenses, empresas de crecimiento menos seguidas, temas calientes, apuestas especulativas y candidatos a evitar.
