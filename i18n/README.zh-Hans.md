[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyInvest

*一个多语言公开研究空间，用于整理带日期的美国股票、行业和低关注度成长公司研究。*

[![Website](https://img.shields.io/badge/Website-earn.lazying.art-0EA5E9?style=for-the-badge)](https://earn.lazying.art)
[![Research](https://img.shields.io/badge/Research-Markdown-111827?style=for-the-badge&logo=markdown&logoColor=white)](../US_Sector_Investment_Matrix_2026-06-13.md)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-lachlanchen-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/lachlanchen)

LazyInvest 收集投资研究笔记，用来区分当前较强的行业、已经拥挤的热门主题、低关注度成长候选、高风险 moonshot，以及应谨慎回避的公司。这个仓库便于后续维护：每篇笔记都有日期、来源链接，并使用 Markdown 编写。

这是研究笔记本，不是个人金融建议。市场数据、公司指引、法律、利率和新闻都会快速变化；使用任何笔记前都应重新核验一手来源。

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## 当前内容

| 文件 | 用途 |
|---|---|
| [US_Sector_Investment_Matrix_2026-06-13.md](../US_Sector_Investment_Matrix_2026-06-13.md) | 持续维护的行业表，覆盖当前较优、热门、低关注度、高风险和回避名单。 |
| [US_Underfollowed_Growth_Stocks_2026-06-13.md](../US_Underfollowed_Growth_Stocks_2026-06-13.md) | 低关注度美国成长股观察清单，包含催化因素和风险。 |
| [AGENTS.md](../AGENTS.md) | 未来更新研究时使用的本地工作规则。 |

## 快速开始

```bash
git clone https://github.com/lachlanchen/LazyInvest.git
cd LazyInvest
ls
```

你可以直接在 GitHub 上打开 Markdown 文件，也可以使用任意 Markdown 查看器。

## 更新流程

1. 选择一篇带日期的笔记进行更新。
2. 刷新一手来源：公司投资者关系页面、SEC 文件、业绩会文字稿、交易所数据和可靠市场数据。
3. 保持 GAAP 与 non-GAAP 指标的区别。
4. 更新假设、来源链接和研究日期。

## 验证

```bash
rg -n "CITATION\\.cff|Source:|not personal financial advice" ../README.md . ../*.md
git diff --check
```

## 引用

如果你在研究中使用 LazyInvest，请引用本仓库。GitHub 会读取 [CITATION.cff](../CITATION.cff)，并在仓库页面显示 **Cite this repository** 面板。

```bibtex
@software{chen_lazyinvest_2026,
  author = {Chen, Lachlan},
  title = {LazyInvest: Dated U.S. Sector and Stock Research Notes},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyInvest}
}
```

## 状态

首次公开发布：2026-06-13。第一批笔记覆盖美国行业、低关注度成长公司、热门主题、投机型机会和回避候选。
