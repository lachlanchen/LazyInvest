[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyInvest

*مساحة عامة متعددة اللغات لملاحظات بحثية مؤرخة عن الأسهم والقطاعات الأمريكية وشركات النمو الأقل متابعة.*

[![Website](https://img.shields.io/badge/Website-earn.lazying.art-0EA5E9?style=for-the-badge)](https://earn.lazying.art)
[![Research](https://img.shields.io/badge/Research-Markdown-111827?style=for-the-badge&logo=markdown&logoColor=white)](../US_Sector_Investment_Matrix_2026-06-13.md)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-lachlanchen-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/lachlanchen)

يجمع LazyInvest ملاحظات بحثية تميز بين قوة القطاعات الحالية، والموضوعات الساخنة المزدحمة، وفرص النمو الأقل ملاحظة، والرهانات عالية المخاطر، والشركات التي يجب تجنبها. صمم هذا المستودع ليسهل تحديثه: كل ملاحظة مؤرخة، وتحتوي على روابط مصادر، ومكتوبة بصيغة Markdown.

هذا دفتر بحثي، وليس نصيحة مالية شخصية. تتغير بيانات السوق، وتوجيهات الشركات، والقوانين، وأسعار الفائدة، والأخبار بسرعة؛ لذلك يجب مراجعة المصادر الأولية قبل استخدام أي ملاحظة.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## المحتويات الحالية

| الملف | الغرض |
|---|---|
| [US_Sector_Investment_Matrix_2026-06-13.md](../US_Sector_Investment_Matrix_2026-06-13.md) | جدول قطاعات محدث يغطي الأفضل حاليا، والموضوعات الساخنة، والفرص الأقل متابعة، والمخاطر العالية، وقائمة التجنب. |
| [US_Underfollowed_Growth_Stocks_2026-06-13.md](../US_Underfollowed_Growth_Stocks_2026-06-13.md) | قائمة متابعة مركزة لشركات نمو أمريكية أقل ملاحظة، مع المحفزات والمخاطر. |
| [AGENTS.md](../AGENTS.md) | قواعد العمل المحلية لتحديثات البحث المستقبلية. |

## البدء السريع

```bash
git clone https://github.com/lachlanchen/LazyInvest.git
cd LazyInvest
ls
```

افتح ملفات Markdown مباشرة على GitHub أو باستخدام أي عارض Markdown.

## سير التحديث

1. اختر ملاحظة مؤرخة للتحديث.
2. حدث المصادر الأولية: علاقات المستثمرين، ملفات SEC، نصوص مكالمات الأرباح، بيانات البورصات، ومصادر السوق الموثوقة.
3. حافظ على الفصل بين مقاييس GAAP و non-GAAP.
4. حدث الافتراضات، وروابط المصادر، وتاريخ البحث.

## التحقق

```bash
rg -n "CITATION\\.cff|Source:|not personal financial advice" ../README.md . ../*.md
git diff --check
```

## الاستشهاد

إذا استخدمت LazyInvest في بحث، فاستشهد بالمستودع. يقرأ GitHub ملف [CITATION.cff](../CITATION.cff) ويعرض لوحة **Cite this repository** في صفحة المستودع.

```bibtex
@software{chen_lazyinvest_2026,
  author = {Chen, Lachlan},
  title = {LazyInvest: Dated U.S. Sector and Stock Research Notes},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyInvest}
}
```

## الحالة

الإصدار العام الأول: 2026-06-13. تغطي الملاحظات الأولى قطاعات الولايات المتحدة، وشركات النمو الأقل متابعة، والموضوعات الساخنة، والرهانات المضاربية، والشركات المرشحة للتجنب.
