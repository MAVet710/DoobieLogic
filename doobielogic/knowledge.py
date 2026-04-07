from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class KnowledgeEntry:
    category: str
    title: str
    content: str
    tags: str
    source_url: str


DEFAULT_KNOWLEDGE: list[KnowledgeEntry] = [
    KnowledgeEntry("terpene", "Myrcene", "Myrcene is a common cannabis terpene associated with earthy aromas and potentially more sedative perceived effects.", "myrcene,terpene,aroma", "https://www.ncbi.nlm.nih.gov/"),
    KnowledgeEntry("terpene", "Limonene", "Limonene is a citrus-forward terpene often discussed with elevated mood and stress-relief perception.", "limonene,terpene,citrus", "https://www.ncbi.nlm.nih.gov/"),
    KnowledgeEntry("terpene", "Pinene", "Pinene terpenes are linked with pine aromas and often discussed for alertness-oriented experiences.", "pinene,terpene,pine", "https://www.ncbi.nlm.nih.gov/"),
    KnowledgeEntry("cannabinoid", "THC", "Delta-9 THC is the primary intoxicating cannabinoid in cannabis.", "thc,cannabinoid,cb1", "https://www.ncbi.nlm.nih.gov/"),
    KnowledgeEntry("cannabinoid", "CBD", "CBD is generally non-intoxicating and commonly studied for inflammation, anxiety, and seizure applications.", "cbd,cannabinoid", "https://www.ncbi.nlm.nih.gov/"),
    KnowledgeEntry("cannabinoid", "CBG", "CBG is a minor cannabinoid and precursor for other cannabinoids in biosynthesis.", "cbg,cannabinoid", "https://www.ncbi.nlm.nih.gov/"),
    KnowledgeEntry("strain", "Chemovar vs strain", "Chemovar data (cannabinoids + terpenes) is more actionable than strain name alone.", "strain,chemovar", "https://www.ncbi.nlm.nih.gov/"),
    KnowledgeEntry("extraction", "Hydrocarbon extraction", "Butane/propane extraction preserves terpene fractions but requires residual solvent controls.", "bho,hydrocarbon,solvent", "https://www.astm.org/"),
    KnowledgeEntry("extraction", "Ethanol extraction", "Ethanol extraction is scalable and commonly used for crude and winterized oils.", "ethanol,extraction,winterization", "https://www.astm.org/"),
    KnowledgeEntry("extraction", "CO2 extraction", "Supercritical CO2 extraction supports tunable parameters and solventless market positioning.", "co2,supercritical,extraction", "https://www.astm.org/"),
    KnowledgeEntry("extraction", "Rosin", "Rosin uses heat and pressure with no solvents and is popular for premium concentrates.", "rosin,solventless", "https://www.leafly.com/"),
    KnowledgeEntry("consumption", "Inhalation", "Smoking and vaping usually have faster onset and shorter duration than oral products.", "inhalation,vape,smoking", "https://www.cdc.gov/cannabis/"),
    KnowledgeEntry("consumption", "Edibles", "Edibles usually have delayed onset (30-120 minutes) and longer duration.", "edible,onset,duration", "https://www.cdc.gov/cannabis/"),
    KnowledgeEntry("consumption", "Tincture", "Sublingual tinctures often have intermediate onset between inhaled and oral edible formats.", "tincture,sublingual", "https://www.ncbi.nlm.nih.gov/"),
    KnowledgeEntry("cultivation", "Integrated pest management", "IPM combines prevention, scouting, and targeted controls to reduce crop losses and compliance risk.", "cultivation,ipm,pests", "https://www.epa.gov/"),
    KnowledgeEntry("cultivation", "Dry and cure", "Dry/cure control stabilizes moisture, preserves terpenes, and helps reduce microbial risk.", "dry,cure,moisture", "https://www.astm.org/"),
    KnowledgeEntry("kitchen", "Edible GMP", "Cannabis kitchens should follow food-grade GMP including sanitation, allergen controls, and lot traceability.", "kitchen,gmp,allergen", "https://www.fda.gov/food"),
    KnowledgeEntry("kitchen", "Infusion homogeneity", "Uniform infusion requires validated mixing and testing for consistent dose per serving.", "kitchen,infusion,homogeneity", "https://www.astm.org/"),
    KnowledgeEntry("infusion", "Nano-emulsion", "Nano-emulsion systems may improve beverage dispersion and onset consistency when process-controlled.", "infusion,nano,beverage", "https://www.ncbi.nlm.nih.gov/"),
    KnowledgeEntry("packaging", "Child-resistant packaging", "Most legal markets require child-resistant packaging and warning language.", "packaging,child resistant,legal", "https://www.cpsc.gov/"),
    KnowledgeEntry("packaging", "Label controls", "Potency claims should match approved CoA results and state label rules.", "packaging,label,potency", "https://cannabis.ca.gov/"),
    KnowledgeEntry("co-pack", "Quality agreement", "Co-pack relationships require written quality agreements for specs, CAPA ownership, and release criteria.", "co-pack,quality,capa", "https://www.fda.gov/"),
    KnowledgeEntry("retail", "Open-to-buy", "Open-to-buy planning helps buyers control inventory risk while maintaining in-stock velocity.", "buyer,otb,inventory", "https://www.shopify.com/retail/open-to-buy"),
    KnowledgeEntry("retail", "Assortment strategy", "Assortment should balance traffic SKUs, premium upsell, and high-repeat staples.", "retail,assortment,buyer", "https://www.nrf.com/"),
    KnowledgeEntry("retail", "Vendor scorecards", "Vendor scorecards on fill rate, defects, and turns improve buying decisions.", "retail,vendor,scorecard", "https://www.nacds.org/"),
    KnowledgeEntry("sales", "Sell-through strategy", "Sales teams should optimize retailer sell-through, not just sell-in volume.", "sales,sell-through,sell-in", "https://www.headset.io/"),
    KnowledgeEntry("sales", "Territory prioritization", "Account prioritization should weigh TAM, win probability, and operational fit.", "sales,territory,pipeline", "https://hbr.org/"),
    KnowledgeEntry("compliance", "Seed-to-sale tracking", "Seed-to-sale systems require accurate package IDs, manifests, and reconciliation.", "compliance,metrc,tracking", "https://www.metrc.com/"),
    KnowledgeEntry("compliance", "Testing compliance", "Regulated markets typically require potency, pesticide, heavy metal, microbial, and solvent tests.", "compliance,testing,lab", "https://cannabis.ca.gov/"),
    KnowledgeEntry("safety", "Start low go slow", "New consumers should start low and wait before re-dosing to reduce overconsumption risk.", "safety,dose,edible", "https://www.cdc.gov/cannabis/"),
]


class CannabisKnowledgeBase:
    def __init__(self, db_path: str | Path = "doobielogic_knowledge.db"):
        self.db_path = Path(db_path)
        self._init_db()
        self._seed_if_empty()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    source_url TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    persona TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    helpful INTEGER NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def _seed_if_empty(self) -> None:
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM knowledge_entries").fetchone()[0]
            if count:
                return
            conn.executemany(
                "INSERT INTO knowledge_entries (category, title, content, tags, source_url) VALUES (?, ?, ?, ?, ?)",
                [(e.category, e.title, e.content, e.tags, e.source_url) for e in DEFAULT_KNOWLEDGE],
            )

    def categories(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT DISTINCT category FROM knowledge_entries ORDER BY category").fetchall()
        return [r[0] for r in rows]

    def ask(self, question: str, limit: int = 5) -> dict:
        tokens = _tokens(question)
        with self._connect() as conn:
            rows = conn.execute("SELECT category, title, content, tags, source_url FROM knowledge_entries").fetchall()

        scored: list[tuple[int, str, str, str, str, str]] = []
        for category, title, content, tags, source_url in rows:
            hay = f"{title} {content} {tags} {category}".lower()
            score = sum(2 if t in title.lower() else 1 for t in tokens if t in hay)
            if score > 0:
                scored.append((score, category, title, content, tags, source_url))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:limit]

        if not top:
            return {
                "question": question,
                "answer": "I couldn't find a direct match in the current cannabis ops knowledge base. Try more specific terms.",
                "matches": [],
            }

        answer = "\n".join(f"- {title}: {content}" for _, _, title, content, _, _ in top[:3])
        matches = [
            {
                "category": category,
                "title": title,
                "content": content,
                "tags": tags,
                "source_url": source_url,
                "score": score,
            }
            for score, category, title, content, tags, source_url in top
        ]
        return {"question": question, "answer": answer, "matches": matches}

    def learn_from_feedback(self, persona: str, question: str, answer: str, helpful: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO feedback_log (persona, question, answer, helpful) VALUES (?, ?, ?, ?)",
                (persona, question, answer, 1 if helpful else 0),
            )
            if helpful and len(question) > 8 and len(answer) > 20:
                conn.execute(
                    "INSERT INTO knowledge_entries (category, title, content, tags, source_url) VALUES (?, ?, ?, ?, ?)",
                    (
                        "playbook",
                        f"Learned: {question[:60]}",
                        answer[:500],
                        f"{persona},learned,feedback",
                        "https://internal.doobielogic.local/feedback",
                    ),
                )


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z0-9\-]+", text.lower()) if len(t) > 2]
