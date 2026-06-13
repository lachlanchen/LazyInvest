[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyInvest

*一個多語言公開研究空間，用於整理帶日期的美國股票、產業與低關注度成長公司研究。*

[![Website](https://img.shields.io/badge/Website-earn.lazying.art-0EA5E9?style=for-the-badge)](https://earn.lazying.art)
[![Research](https://img.shields.io/badge/Research-Markdown-111827?style=for-the-badge&logo=markdown&logoColor=white)](../US_Sector_Investment_Matrix_2026-06-13.md)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-lachlanchen-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/lachlanchen)

LazyInvest 收集投資研究筆記，用來區分目前較強的產業、已經擁擠的熱門主題、低關注度成長候選、高風險 moonshot，以及應謹慎迴避的公司。這個倉庫便於後續維護：每篇筆記都有日期、來源連結，並使用 Markdown 編寫。

這是研究筆記本，不是個人金融建議。市場資料、公司指引、法律、利率和新聞都會快速變化；使用任何筆記前都應重新核驗一手來源。

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## 目前內容

| 檔案 | 用途 |
|---|---|
| [US_Sector_Investment_Matrix_2026-06-13.md](../US_Sector_Investment_Matrix_2026-06-13.md) | 持續維護的產業表，涵蓋目前較優、熱門、低關注度、高風險和迴避名單。 |
| [US_Underfollowed_Growth_Stocks_2026-06-13.md](../US_Underfollowed_Growth_Stocks_2026-06-13.md) | 低關注度美國成長股觀察清單，包含催化因素和風險。 |
| [AGENTS.md](../AGENTS.md) | 未來更新研究時使用的本地工作規則。 |

## 快速開始

```bash
git clone https://github.com/lachlanchen/LazyInvest.git
cd LazyInvest
ls
```

你可以直接在 GitHub 上打開 Markdown 檔案，也可以使用任意 Markdown 檢視器。

## 更新流程

1. 選擇一篇帶日期的筆記進行更新。
2. 刷新一手來源：公司投資者關係頁面、SEC 文件、業績會文字稿、交易所資料和可靠市場資料。
3. 保持 GAAP 與 non-GAAP 指標的區別。
4. 更新假設、來源連結和研究日期。

## 驗證

```bash
rg -n "CITATION\\.cff|Source:|not personal financial advice" ../README.md . ../*.md
git diff --check
```

## 引用

如果你在研究中使用 LazyInvest，請引用本倉庫。GitHub 會讀取 [CITATION.cff](../CITATION.cff)，並在倉庫頁面顯示 **Cite this repository** 面板。

```bibtex
@software{chen_lazyinvest_2026,
  author = {Chen, Lachlan},
  title = {LazyInvest: Dated U.S. Sector and Stock Research Notes},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyInvest}
}
```

## 狀態

首次公開發布：2026-06-13。第一批筆記涵蓋美國產業、低關注度成長公司、熱門主題、投機型機會和迴避候選。
