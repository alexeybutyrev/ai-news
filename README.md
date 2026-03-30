# 🤖 AI News Daily

[![Updated](https://img.shields.io/badge/Updated-Daily-blue?style=flat-square)](https://alexeybutyrev.github.io/ai-news/)
[![Sources](https://img.shields.io/badge/Sources-14-green?style=flat-square)](https://github.com/alexeybutyrev/ai-news)

> AI-curated daily news from top tech sources, with TLDR summaries and relevance ranking.

## 📰 Sources

| Source | Priority | Focus |
|--------|----------|-------|
| TechCrunch AI | 1 | AI startups, product launches |
| MIT Tech Review | 1 | Research, analysis |
| VentureBeat | 1 | Enterprise AI, funding |
| Latent Space | 1 | AI engineering, podcasts |
| Hugging Face Blog | 2 | ML research, open source |
| DeepMind | 2 | Research breakthroughs |
| Wired | 2 | Consumer AI, deep dives |
| Ars Technica | 2 | Technical coverage |
| Interconnects | 2 | AI analysis |
| Reuters AI | 2 | Industry news |

**Blocked by Substack (403):**
- AlphaSignal
- The Sequence

## 🤖 Features

- ✅ Top 6-10 AI stories selected by relevance
- ✅ AI-generated TLDR summaries
- ✅ Source diversity (max 2-3 per source)
- ✅ AI-relevance filtering (non-AI tech filtered out)
- ✅ Expand to 7 days if slow news day
- ✅ Updated daily at 6:00 AM UTC
- ✅ Archive of past 30 days

## 🔗 Live

**https://alexeybutyrev.github.io/ai-news/**

## 📁 Structure

```
ai-news/
├── docs/
│   ├── index.html      # GitHub Pages frontend
│   ├── news.json       # Latest news data
│   └── archive/        # Historical news (30 days)
├── scraper.py          # News aggregator
├── .github/workflows/  # CI/CD automation
└── README.md
```

## 🔄 How It Works

1. **Fetch** RSS feeds from 14 sources
2. **Filter** for AI-relevant content (keyword + relevance score)
3. **Expand** to last 7 days if fewer than 5 articles from yesterday
4. **Rank** by relevance score (AI keywords, source priority)
5. **Diversify** max 2-3 articles per source
6. **Generate** TLDR summaries
7. **Push** to GitHub Pages

## 🛠️ Tech Stack

- Python 3.11 (stdlib only - no dependencies)
- GitHub Actions for automation
- GitHub Pages for hosting

---

Made with ❤️ by [Alexey Butyrev](https://github.com/alexeybutyrev)
