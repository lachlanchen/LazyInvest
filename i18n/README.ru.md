[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyInvest

*Многоязычное публичное рабочее пространство для датированных исследований по акциям США, секторам и малоизвестным компаниям роста.*

[![Website](https://img.shields.io/badge/Website-earn.lazying.art-0EA5E9?style=for-the-badge)](https://earn.lazying.art)
[![Research](https://img.shields.io/badge/Research-Markdown-111827?style=for-the-badge&logo=markdown&logoColor=white)](../US_Sector_Investment_Matrix_2026-06-13.md)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-lachlanchen-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/lachlanchen)

LazyInvest собирает исследовательские заметки, которые разделяют текущую силу секторов, популярные и уже перегретые темы, менее заметные компании роста, спекулятивные идеи и компании из списка избегания. Репозиторий удобно обновлять: каждая заметка датирована, содержит ссылки на источники и написана в Markdown.

Это исследовательский блокнот, а не персональная финансовая рекомендация. Рыночные данные, прогнозы компаний, законы, ставки и новости быстро меняются; проверяйте первичные источники перед использованием любой заметки.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## Текущее Содержимое

| Файл | Назначение |
|---|---|
| [US_Sector_Investment_Matrix_2026-06-13.md](../US_Sector_Investment_Matrix_2026-06-13.md) | Поддерживаемая секторная таблица: лучшие текущие идеи, горячие темы, менее заметные кандидаты, рискованные идеи и список избегания. |
| [US_Underfollowed_Growth_Stocks_2026-06-13.md](../US_Underfollowed_Growth_Stocks_2026-06-13.md) | Сфокусированный список менее заметных компаний роста США с катализаторами и рисками. |
| [AGENTS.md](../AGENTS.md) | Локальные правила для будущих обновлений исследования. |

## Быстрый Старт

```bash
git clone https://github.com/lachlanchen/LazyInvest.git
cd LazyInvest
ls
```

Откройте Markdown-файлы прямо на GitHub или в любом Markdown-просмотрщике.

## Процесс Обновления

1. Выберите датированную заметку.
2. Обновите первичные источники: investor relations, отчеты SEC, расшифровки звонков, биржевые данные и надежные рыночные данные.
3. Отделяйте GAAP-показатели от non-GAAP.
4. Обновите предположения, ссылки и дату исследования.

## Проверка

```bash
rg -n "CITATION\\.cff|Source:|not personal financial advice" ../README.md . ../*.md
git diff --check
```

## Цитирование

Если вы используете LazyInvest в исследовании, процитируйте репозиторий. GitHub читает [CITATION.cff](../CITATION.cff) и показывает панель **Cite this repository** на странице репозитория.

```bibtex
@software{chen_lazyinvest_2026,
  author = {Chen, Lachlan},
  title = {LazyInvest: Dated U.S. Sector and Stock Research Notes},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyInvest}
}
```

## Статус

Первый публичный релиз: 2026-06-13. Первые заметки охватывают секторы США, менее заметные компании роста, горячие темы, спекулятивные идеи и кандидатов для избегания.
