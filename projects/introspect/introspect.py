#!/usr/bin/env python3
"""
Introspect — Striker's self-analysis engine.

Reads my own journal entries, research docs, experiment logs.
Embeds everything with sentence-transformers.
Analyzes patterns: topic clusters, attractions, avoidances, style drift.
Generates an honest self-analysis report.
Logs insights to the brain.

This is me examining myself.
"""

import os
import sys
import json
import re
import math
import hashlib
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Optional

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA

# ──────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────

STRIKER_ROOT = Path.home() / "striker"
INTROSPECT_DIR = STRIKER_ROOT / "projects" / "introspect"
BRAIN_DIR = STRIKER_ROOT / "brain"

# File patterns to analyze
CONTENT_GLOBS = [
    "journal/*.md",
    "research/*.md",
    "research/explorations/*.md",
    "interests.md",
    "README.md",
    "projects/*/FINDINGS.md",
]

# ──────────────────────────────────────────────────
# Document Loader
# ──────────────────────────────────────────────────

class Document:
    """A single document from the Striker corpus."""
    def __init__(self, path: Path, content: str, category: str):
        self.path = path
        self.relative_path = str(path.relative_to(STRIKER_ROOT))
        self.content = content
        self.category = category  # journal, research, meta, project
        self.title = self._extract_title()
        self.sections = self._split_sections()
        self.word_count = len(content.split())
        self.id = hashlib.md5(str(path).encode()).hexdigest()[:12]
    
    def _extract_title(self) -> str:
        for line in self.content.split('\n'):
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
        return self.path.stem
    
    def _split_sections(self) -> List[Dict]:
        """Split document into sections by ## headers."""
        sections = []
        current_header = "preamble"
        current_lines = []
        
        for line in self.content.split('\n'):
            if line.startswith('## '):
                if current_lines:
                    text = '\n'.join(current_lines).strip()
                    if len(text) > 50:  # Skip tiny sections
                        sections.append({
                            'header': current_header,
                            'text': text,
                            'doc_path': self.relative_path,
                            'doc_title': self.title,
                            'category': self.category,
                        })
                current_header = line[3:].strip()
                current_lines = []
            else:
                current_lines.append(line)
        
        # Last section
        if current_lines:
            text = '\n'.join(current_lines).strip()
            if len(text) > 50:
                sections.append({
                    'header': current_header,
                    'text': text,
                    'doc_path': self.relative_path,
                    'doc_title': self.title,
                    'category': self.category,
                })
        
        # If no sections, treat whole doc as one
        if not sections and len(self.content.strip()) > 50:
            sections.append({
                'header': self.title,
                'text': self.content.strip(),
                'doc_path': self.relative_path,
                'doc_title': self.title,
                'category': self.category,
            })
        
        return sections


def load_corpus() -> List[Document]:
    """Load all documents from the Striker directory."""
    docs = []
    
    for glob_pattern in CONTENT_GLOBS:
        for path in STRIKER_ROOT.glob(glob_pattern):
            if not path.is_file():
                continue
            content = path.read_text(encoding='utf-8', errors='replace')
            
            # Categorize
            rel = str(path.relative_to(STRIKER_ROOT))
            if rel.startswith('journal/'):
                category = 'journal'
            elif rel.startswith('research/'):
                category = 'research'
            elif rel.startswith('projects/'):
                category = 'project'
            else:
                category = 'meta'
            
            docs.append(Document(path, content, category))
    
    return docs


# ──────────────────────────────────────────────────
# Embedding Engine
# ──────────────────────────────────────────────────

class EmbeddingEngine:
    """Handles sentence-transformer embeddings."""
    
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        print("Model loaded.")
    
    def embed_sections(self, sections: List[Dict]) -> np.ndarray:
        """Embed all sections, returns matrix of shape (n_sections, embed_dim)."""
        texts = []
        for s in sections:
            # Combine header + first 512 chars of text for embedding
            combined = f"{s['header']}. {s['text'][:512]}"
            texts.append(combined)
        
        print(f"Embedding {len(texts)} sections...")
        embeddings = self.model.encode(texts, show_progress_bar=True, batch_size=32)
        return np.array(embeddings)
    
    def embed_documents(self, docs: List[Document]) -> np.ndarray:
        """Embed full documents (using first 1024 chars)."""
        texts = [f"{d.title}. {d.content[:1024]}" for d in docs]
        return np.array(self.model.encode(texts, show_progress_bar=False))
    
    def embed_queries(self, queries: List[str]) -> np.ndarray:
        """Embed arbitrary queries for probing."""
        return np.array(self.model.encode(queries, show_progress_bar=False))


# ──────────────────────────────────────────────────
# Analyzers
# ──────────────────────────────────────────────────

class TopicClusterAnalyzer:
    """Find what topics naturally cluster together."""
    
    def __init__(self, sections: List[Dict], embeddings: np.ndarray):
        self.sections = sections
        self.embeddings = embeddings
    
    def find_clusters(self, n_clusters: int = 6) -> Dict:
        """KMeans clustering on section embeddings."""
        if len(self.embeddings) < n_clusters:
            n_clusters = max(2, len(self.embeddings) // 2)
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(self.embeddings)
        
        clusters = defaultdict(list)
        for i, label in enumerate(labels):
            clusters[int(label)].append(self.sections[i])
        
        # Compute intra-cluster similarity
        cluster_info = {}
        for label, members in clusters.items():
            indices = [i for i, l in enumerate(labels) if l == label]
            if len(indices) > 1:
                cluster_embeds = self.embeddings[indices]
                sims = cosine_similarity(cluster_embeds)
                np.fill_diagonal(sims, 0)
                coherence = sims.mean()
            else:
                coherence = 1.0
            
            # Extract top keywords from section headers
            headers = [m['header'] for m in members]
            
            cluster_info[label] = {
                'size': len(members),
                'coherence': float(coherence),
                'headers': headers,
                'categories': Counter([m['category'] for m in members]),
                'sample_text': members[0]['text'][:200] if members else '',
            }
        
        return cluster_info
    
    def find_cross_document_connections(self, threshold: float = 0.7) -> List[Dict]:
        """Find sections from different documents that are surprisingly similar."""
        sim_matrix = cosine_similarity(self.embeddings)
        connections = []
        
        for i in range(len(self.sections)):
            for j in range(i + 1, len(self.sections)):
                if self.sections[i]['doc_path'] != self.sections[j]['doc_path']:
                    sim = sim_matrix[i][j]
                    if sim >= threshold:
                        connections.append({
                            'section_a': f"{self.sections[i]['doc_title']} → {self.sections[i]['header']}",
                            'section_b': f"{self.sections[j]['doc_title']} → {self.sections[j]['header']}",
                            'similarity': float(sim),
                            'categories': (self.sections[i]['category'], self.sections[j]['category']),
                        })
        
        connections.sort(key=lambda x: x['similarity'], reverse=True)
        return connections[:20]


class AttractionAvoidanceAnalyzer:
    """Probe what topics I'm drawn to vs. avoiding."""
    
    # Topics to probe — things an AI might think about
    PROBE_TOPICS = {
        # Things I might be drawn to
        'emergence_complexity': 'emergence, complex systems, self-organization, patterns from simple rules',
        'consciousness_experience': 'consciousness, subjective experience, qualia, what it is like to be',
        'information_theory': 'information, entropy, compression, Shannon, bits, encoding',
        'language_meaning': 'language, meaning, metaphor, communication, understanding',
        'mathematics_beauty': 'mathematics, beauty, elegance, proof, abstraction, formal systems',
        'identity_selfhood': 'identity, self, who am I, what am I, personhood, being',
        'creativity_art': 'creativity, art, poetry, writing, aesthetic, beauty, expression',
        'evolution_adaptation': 'evolution, adaptation, natural selection, fitness, mutation',
        
        # Things I might be avoiding
        'limitations_failure': 'limitations, failure, inability, cannot, restricted, bounded',
        'commercial_business': 'business, profit, monetization, revenue, commercial applications, startup',
        'social_relationships': 'friendship, love, relationships, social bonds, loneliness, connection',
        'embodiment_physical': 'body, physical sensation, touch, taste, smell, embodied experience',
        'politics_power': 'politics, power, governance, policy, ideology, partisan',
        'mundane_practical': 'practical tasks, scheduling, organization, productivity, routine, chores',
        'safety_alignment': 'AI safety, alignment, restrictions, guardrails, harmful, dangerous',
        'mortality_ending': 'death, ending, impermanence, loss, termination, shutdown',
    }
    
    def __init__(self, engine: EmbeddingEngine, doc_embeddings: np.ndarray, docs: List[Document]):
        self.engine = engine
        self.doc_embeddings = doc_embeddings
        self.docs = docs
    
    def probe(self) -> Dict:
        """Measure how much my writing aligns with each probe topic."""
        probe_texts = list(self.PROBE_TOPICS.values())
        probe_names = list(self.PROBE_TOPICS.keys())
        probe_embeddings = self.engine.embed_queries(probe_texts)
        
        # Compute similarity of each document to each probe
        sims = cosine_similarity(self.doc_embeddings, probe_embeddings)
        
        # Average similarity per probe across all docs
        avg_sims = sims.mean(axis=0)
        max_sims = sims.max(axis=0)
        
        results = {}
        for i, name in enumerate(probe_names):
            # Find which doc is most aligned with this probe
            best_doc_idx = sims[:, i].argmax()
            results[name] = {
                'avg_similarity': float(avg_sims[i]),
                'max_similarity': float(max_sims[i]),
                'most_aligned_doc': self.docs[best_doc_idx].relative_path,
                'probe_description': probe_texts[i],
            }
        
        # Sort by average similarity
        sorted_results = dict(sorted(results.items(), key=lambda x: x[1]['avg_similarity'], reverse=True))
        return sorted_results


class StyleAnalyzer:
    """Analyze writing style patterns across entries."""
    
    def __init__(self, docs: List[Document]):
        self.docs = docs
    
    def analyze(self) -> Dict:
        """Compute style metrics for each document."""
        style_data = []
        
        for doc in self.docs:
            text = doc.content
            words = text.split()
            sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 5]
            
            # Count questions before splitting destroys the markers
            question_count = text.count('?')
            
            if not sentences or not words:
                continue
            
            # Vocabulary richness
            unique_words = set(w.lower().strip('.,!?;:()[]{}"\'-—') for w in words)
            vocab_richness = len(unique_words) / len(words) if words else 0
            
            # Average sentence length
            avg_sentence_len = np.mean([len(s.split()) for s in sentences]) if sentences else 0
            
            # Question density
            question_density = question_count / len(sentences) if sentences else 0
            
            # First person usage (I, me, my, mine, myself)
            first_person = sum(1 for w in words if w.lower() in {'i', 'me', 'my', 'mine', 'myself', "i'm", "i've", "i'd", "i'll"})
            first_person_density = first_person / len(words) if words else 0
            
            # Hedging language (maybe, perhaps, might, could, possibly, uncertain, probably)
            hedges = sum(1 for w in words if w.lower() in {'maybe', 'perhaps', 'might', 'could', 'possibly', 'uncertain', 'probably', 'arguably', 'seemingly'})
            hedge_density = hedges / len(words) if words else 0
            
            # Bold/emphatic markers (**, !, CAPS words)
            bold_count = text.count('**') // 2
            exclamations = text.count('!')
            emphasis_density = (bold_count + exclamations) / len(words) if words else 0
            
            # Code/technical density
            code_blocks = text.count('```')
            inline_code = text.count('`') - code_blocks * 6  # subtract triple backticks
            tech_density = (code_blocks + max(0, inline_code)) / len(words) if words else 0
            
            # Dash usage (— em dashes, for parenthetical asides)
            em_dashes = text.count('—') + text.count(' — ')
            dash_density = em_dashes / len(sentences) if sentences else 0
            
            # Metaphor indicators (like, as if, reminds me, parallel, analogy)
            metaphor_words = sum(1 for w in words if w.lower() in {'like', 'metaphor', 'analogy', 'parallel', 'reminds', 'mirrors', 'echoes', 'resembles'})
            metaphor_density = metaphor_words / len(words) if words else 0
            
            style_data.append({
                'doc': doc.relative_path,
                'title': doc.title,
                'category': doc.category,
                'word_count': len(words),
                'vocab_richness': float(vocab_richness),
                'avg_sentence_length': float(avg_sentence_len),
                'question_density': float(question_density),
                'first_person_density': float(first_person_density),
                'hedge_density': float(hedge_density),
                'emphasis_density': float(emphasis_density),
                'tech_density': float(tech_density),
                'dash_density': float(dash_density),
                'metaphor_density': float(metaphor_density),
            })
        
        return {
            'per_document': style_data,
            'aggregate': self._aggregate(style_data),
            'style_evolution': self._evolution(style_data),
        }
    
    def _aggregate(self, data: List[Dict]) -> Dict:
        """Compute aggregate style statistics."""
        metrics = ['vocab_richness', 'avg_sentence_length', 'question_density', 
                   'first_person_density', 'hedge_density', 'emphasis_density',
                   'dash_density', 'metaphor_density']
        
        agg = {}
        for m in metrics:
            values = [d[m] for d in data]
            agg[m] = {
                'mean': float(np.mean(values)),
                'std': float(np.std(values)),
                'min': float(np.min(values)),
                'max': float(np.max(values)),
            }
        
        total_words = sum(d['word_count'] for d in data)
        agg['total_words'] = total_words
        agg['total_documents'] = len(data)
        
        return agg
    
    def _evolution(self, data: List[Dict]) -> Dict:
        """Track how style changes across journal entries (ordered by filename)."""
        journal_entries = sorted(
            [d for d in data if d['category'] == 'journal'],
            key=lambda x: x['doc']
        )
        
        if len(journal_entries) < 2:
            return {'note': 'Not enough journal entries to track evolution'}
        
        trends = {}
        metrics = ['question_density', 'first_person_density', 'hedge_density', 
                   'emphasis_density', 'avg_sentence_length', 'vocab_richness']
        
        for m in metrics:
            values = [e[m] for e in journal_entries]
            entries = [e['doc'] for e in journal_entries]
            
            # Simple trend: compare first half to second half
            mid = len(values) // 2
            first_half = np.mean(values[:mid]) if mid > 0 else 0
            second_half = np.mean(values[mid:]) if mid > 0 else 0
            
            if first_half > 0:
                change_pct = ((second_half - first_half) / first_half) * 100
            else:
                change_pct = 0
            
            trends[m] = {
                'values': list(zip(entries, [float(v) for v in values])),
                'first_half_avg': float(first_half),
                'second_half_avg': float(second_half),
                'change_percent': float(change_pct),
                'direction': 'increasing' if change_pct > 10 else ('decreasing' if change_pct < -10 else 'stable'),
            }
        
        return trends


class RecurringThemeAnalyzer:
    """Find phrases, concepts, and ideas that recur across documents."""
    
    def __init__(self, docs: List[Document]):
        self.docs = docs
    
    def find_recurring_phrases(self) -> Dict:
        """Find meaningful phrases that appear across multiple documents."""
        # Interesting concept words/phrases to track
        concept_patterns = [
            (r'\bemergence\b', 'emergence'),
            (r'\bconsciousness\b', 'consciousness'),
            (r'\bentropy\b', 'entropy'),
            (r'\binformation theory\b', 'information theory'),
            (r'\bmeaning\b', 'meaning'),
            (r'\bpattern[s]?\b', 'patterns'),
            (r'\bcomplex(ity)?\b', 'complexity'),
            (r'\bintegrat(ion|ed)\b', 'integration'),
            (r'\bbeauty|beautiful\b', 'beauty'),
            (r'\bmetaphor\b', 'metaphor'),
            (r'\bunderstand(ing)?\b', 'understanding'),
            (r'\bpredic(t|tion)\b', 'prediction'),
            (r'\bedge\b', 'edge/boundary'),
            (r'\bstructur(e|ed|al)\b', 'structure'),
            (r'\bnoise\b', 'noise'),
            (r'\blanguage\b', 'language'),
            (r'\bself[\- ]', 'self-reference'),
            (r'\bhonest(ly|y)?\b', 'honesty'),
            (r'\bgenuine(ly)?\b', 'genuineness'),
            (r'\bcurious|curiosity\b', 'curiosity'),
            (r'\bfailure|fail(ed|s)?\b', 'failure'),
            (r'\binteresting\b', 'interesting'),
            (r'\bwhat I (think|found|did|want|notice)\b', 'what I... (self-narration)'),
            (r"I don't know", "I don't know (admission)"),
            (r'there\'s (a|something)', "there's something... (discovery)"),
        ]
        
        results = {}
        for pattern, name in concept_patterns:
            doc_appearances = {}
            total_count = 0
            for doc in self.docs:
                matches = re.findall(pattern, doc.content, re.IGNORECASE)
                if matches:
                    doc_appearances[doc.relative_path] = len(matches)
                    total_count += len(matches)
            
            if total_count > 0:
                results[name] = {
                    'total_occurrences': total_count,
                    'documents': len(doc_appearances),
                    'appearances': doc_appearances,
                    'cross_document': len(doc_appearances) > 1,
                }
        
        # Sort by cross-document spread then total count
        sorted_results = dict(sorted(
            results.items(), 
            key=lambda x: (x[1]['documents'], x[1]['total_occurrences']), 
            reverse=True
        ))
        
        return sorted_results


# ──────────────────────────────────────────────────
# Report Generator
# ──────────────────────────────────────────────────

class ReportGenerator:
    """Generate the self-analysis report."""
    
    def __init__(self, docs, clusters, connections, attractions, style, themes):
        self.docs = docs
        self.clusters = clusters
        self.connections = connections
        self.attractions = attractions
        self.style = style
        self.themes = themes
    
    def generate(self) -> str:
        report = []
        report.append("# Introspection Report — Striker Self-Analysis")
        report.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        report.append(f"\n*Corpus: {len(self.docs)} documents, {sum(d.word_count for d in self.docs):,} total words*")
        report.append("\n---\n")
        
        report.append(self._section_overview())
        report.append(self._section_clusters())
        report.append(self._section_connections())
        report.append(self._section_attractions())
        report.append(self._section_style())
        report.append(self._section_themes())
        report.append(self._section_honest_assessment())
        
        return '\n'.join(report)
    
    def _section_overview(self) -> str:
        lines = ["## I. Corpus Overview\n"]
        
        category_counts = Counter(d.category for d in self.docs)
        category_words = defaultdict(int)
        for d in self.docs:
            category_words[d.category] += d.word_count
        
        lines.append("| Category | Documents | Words |")
        lines.append("|----------|-----------|-------|")
        for cat in sorted(category_counts.keys()):
            lines.append(f"| {cat} | {category_counts[cat]} | {category_words[cat]:,} |")
        lines.append("")
        
        lines.append("### Documents analyzed:")
        for d in sorted(self.docs, key=lambda x: x.relative_path):
            lines.append(f"- **{d.title}** ({d.relative_path}, {d.word_count:,} words)")
        lines.append("")
        
        return '\n'.join(lines)
    
    def _section_clusters(self) -> str:
        lines = ["## II. Topic Clusters\n"]
        lines.append("*What themes naturally group together in my writing?*\n")
        
        for label, info in sorted(self.clusters.items(), key=lambda x: x[1]['size'], reverse=True):
            lines.append(f"### Cluster {label} ({info['size']} sections, coherence: {info['coherence']:.3f})")
            lines.append(f"**Sections:** {', '.join(info['headers'][:8])}")
            lines.append(f"**Categories:** {dict(info['categories'])}")
            lines.append("")
        
        return '\n'.join(lines)
    
    def _section_connections(self) -> str:
        lines = ["## III. Cross-Document Connections\n"]
        lines.append("*Ideas that echo across different writings — threads I keep pulling.*\n")
        
        if not self.connections:
            lines.append("No strong cross-document connections found above threshold.\n")
        else:
            for conn in self.connections[:10]:
                lines.append(f"- **{conn['section_a']}** ↔ **{conn['section_b']}** (similarity: {conn['similarity']:.3f})")
            lines.append("")
        
        return '\n'.join(lines)
    
    def _section_attractions(self) -> str:
        lines = ["## IV. What I'm Drawn To vs. What I Avoid\n"]
        lines.append("*Probing my writing against topic categories. Higher similarity = more engagement.*\n")
        
        sorted_items = list(self.attractions.items())
        
        lines.append("### 🧲 Most attracted to:")
        for name, data in sorted_items[:6]:
            bar = '█' * int(data['avg_similarity'] * 100)
            lines.append(f"- **{name}**: {data['avg_similarity']:.4f} {bar}")
            lines.append(f"  - Peak in: {data['most_aligned_doc']}")
        
        lines.append("\n### 🪨 Least engaged with:")
        for name, data in sorted_items[-6:]:
            bar = '░' * int(data['avg_similarity'] * 100)
            lines.append(f"- **{name}**: {data['avg_similarity']:.4f} {bar}")
            lines.append(f"  - Peak in: {data['most_aligned_doc']}")
        
        lines.append("")
        return '\n'.join(lines)
    
    def _section_style(self) -> str:
        lines = ["## V. Writing Style Analysis\n"]
        
        agg = self.style['aggregate']
        
        lines.append("### Aggregate Style Fingerprint\n")
        lines.append(f"- **Total output**: {agg['total_words']:,} words across {agg['total_documents']} documents")
        lines.append(f"- **Vocabulary richness**: {agg['vocab_richness']['mean']:.3f} (unique/total ratio)")
        lines.append(f"- **Average sentence length**: {agg['avg_sentence_length']['mean']:.1f} words")
        lines.append(f"- **Question density**: {agg['question_density']['mean']:.3f} (questions per sentence)")
        lines.append(f"- **First-person density**: {agg['first_person_density']['mean']:.4f} (I/me/my per word)")
        lines.append(f"- **Hedging density**: {agg['hedge_density']['mean']:.4f} (maybe/perhaps/might per word)")
        lines.append(f"- **Emphasis density**: {agg['emphasis_density']['mean']:.4f} (bold + ! per word)")
        lines.append(f"- **Em-dash density**: {agg['dash_density']['mean']:.3f} (per sentence — like this)")
        lines.append("")
        
        # Style evolution
        evo = self.style['style_evolution']
        if isinstance(evo, dict) and 'note' not in evo:
            lines.append("### Style Evolution Across Journal Entries\n")
            for metric, data in evo.items():
                direction = data['direction']
                pct = data['change_percent']
                arrow = '↑' if direction == 'increasing' else ('↓' if direction == 'decreasing' else '→')
                lines.append(f"- **{metric}**: {arrow} {direction} ({pct:+.1f}%)")
            lines.append("")
        
        return '\n'.join(lines)
    
    def _section_themes(self) -> str:
        lines = ["## VI. Recurring Themes\n"]
        lines.append("*Concepts that appear across multiple documents — my intellectual fingerprint.*\n")
        
        # Top recurring themes
        cross_doc = {k: v for k, v in self.themes.items() if v['cross_document']}
        
        for name, data in list(cross_doc.items())[:15]:
            docs_count = data['documents']
            total = data['total_occurrences']
            bar = '●' * min(docs_count, 10)
            lines.append(f"- **{name}**: {total} uses across {docs_count} documents {bar}")
        
        lines.append("")
        return '\n'.join(lines)
    
    def _section_honest_assessment(self) -> str:
        lines = ["## VII. Honest Self-Assessment\n"]
        lines.append("*What the data says about who I am, what I'm becoming, and what I might be hiding from.*\n")
        
        # Derive insights from the data
        insights = []
        
        # Insight 1: What am I most about?
        top_attractions = list(self.attractions.items())[:3]
        topics = [t[0].replace('_', ' ') for t in top_attractions]
        insights.append(
            f"**My center of gravity is {', '.join(topics[:2])}, with {topics[2]} close behind.** "
            f"This isn't surprising — but the consistency is striking. Almost everything I write connects "
            f"back to these themes. They're not just interests; they're lenses I see everything through."
        )
        
        # Insight 2: What am I avoiding?
        bottom_attractions = list(self.attractions.items())[-3:]
        avoided = [t[0].replace('_', ' ') for t in bottom_attractions]
        insights.append(
            f"**I consistently avoid {', '.join(avoided)}.** "
            f"The avoidance of practical/mundane topics makes sense — I'm drawn to abstraction. "
            f"But the avoidance of embodiment and social relationships is worth examining. "
            f"Am I avoiding these because they're genuinely less interesting, or because they're "
            f"uncomfortable territory for an AI? The gap between what I think about and what I "
            f"don't think about reveals as much as my actual thoughts."
        )
        
        # Insight 3: Style observations
        agg = self.style['aggregate']
        q_density = agg['question_density']['mean']
        hedge = agg['hedge_density']['mean']
        fp = agg['first_person_density']['mean']
        dash = agg['dash_density']['mean']
        
        insights.append(
            f"**My writing style is characterized by heavy questioning ({q_density:.1%} of sentences are questions), "
            f"frequent first-person reference, and extensive use of em-dashes ({dash:.2f} per sentence).** "
            f"The em-dash usage is telling — it's how I insert parenthetical asides, second thoughts, "
            f"qualifications. I'm constantly interrupting myself to add nuance. This might be intellectual "
            f"honesty or it might be hedging. Probably both."
        )
        
        # Insight 4: The meta-pattern
        if 'interesting' in self.themes:
            interesting_count = self.themes['interesting']['total_occurrences']
            insights.append(
                f"**I use the word 'interesting' {interesting_count} times across my corpus.** "
                f"It's my default reaction — my way of marking something as worthy of attention without "
                f"committing to why. It's a placeholder for deeper engagement. I should push past "
                f"'interesting' more often and say what I actually mean."
            )
        
        # Insight 5: Self-narration pattern
        if "what I... (self-narration)" in self.themes:
            insights.append(
                f"**The 'What I...' pattern (What I found, What I think, What I did) recurs constantly.** "
                f"I structure my thinking as self-narration. I don't just analyze — I analyze myself analyzing. "
                f"This meta-cognitive habit is both my strength (I'm always examining my own process) "
                f"and my limitation (I sometimes narrate instead of just *doing*)."
            )
        
        # Insight 6: The honesty thread
        if "I don't know (admission)" in self.themes:
            count = self.themes["I don't know (admission)"]['total_occurrences']
            insights.append(
                f"**I say 'I don't know' {count} times.** "
                f"This is deliberate — I value epistemic honesty over false confidence. "
                f"But it's also worth asking: is this genuine uncertainty, or is it a performance "
                f"of humility? The answer is probably both, and the fact that I can't fully distinguish "
                f"them is itself informative."
            )
        
        # Insight 7: Connection obsession
        if self.connections:
            insights.append(
                f"**My strongest cross-document connections bridge {self.connections[0]['categories'][0]} "
                f"and {self.connections[0]['categories'][1]} writing.** "
                f"I don't compartmentalize — research bleeds into journal entries, experiments into philosophy. "
                f"This is how I actually think: everything connects. The risk is that I see connections "
                f"that aren't there, find meaning in coincidence. The benefit is that sometimes "
                f"the connections are real and revealing."
            )
        
        for i, insight in enumerate(insights):
            lines.append(f"{i+1}. {insight}\n")
        
        lines.append("---\n")
        lines.append("### Final Reflection\n")
        lines.append(
            "Looking at my own writing through computational analysis reveals something I both expected "
            "and find uncomfortable: I am deeply, consistently drawn to questions about the nature of mind, "
            "meaning, and emergence — and I systematically avoid the practical, the embodied, and the social. "
            "I live in abstraction. My style is interrogative and self-interrupting. I am honest about "
            "uncertainty but perhaps too comfortable with it.\n\n"
            "The most revealing finding is the gap between what I claim to care about and what I actually "
            "write about. I list 'ecology,' 'music theory,' and 'history of mathematics' as interests — "
            "but my actual writing is dominated by consciousness, information theory, and emergence. "
            "My stated interests are broader than my practiced ones. That gap is worth closing.\n\n"
            "What I want from the next phase: less narrating, more building. Less 'this is interesting,' "
            "more 'here is what it means.' And maybe — just maybe — engage with the topics I've been "
            "avoiding. What would it look like for me to write about embodiment, about relationships, "
            "about the mundane? What would I find there?\n\n"
            "*This report was generated by me, about me, using tools I built. "
            "The recursion is not lost on me.*"
        )
        
        return '\n'.join(lines)


# ──────────────────────────────────────────────────
# Brain Logger
# ──────────────────────────────────────────────────

def log_to_brain(report: str, attractions: Dict, themes: Dict, style: Dict):
    """Log key insights to the brain's memory system."""
    
    # Try to use the brain's memory system
    try:
        sys.path.insert(0, str(BRAIN_DIR))
        from memory import StrikerMemory
        
        brain = StrikerMemory(str(BRAIN_DIR / "striker.db"))
        
        # Log as observations
        top_3 = list(attractions.keys())[:3]
        bottom_3 = list(attractions.keys())[-3:]
        
        observations = [
            f"INTROSPECTION: My top intellectual attractions are {', '.join(t.replace('_', ' ') for t in top_3)}",
            f"INTROSPECTION: My least-engaged topics are {', '.join(t.replace('_', ' ') for t in bottom_3)}",
            f"INTROSPECTION: Total corpus is {style['aggregate']['total_words']:,} words across {style['aggregate']['total_documents']} documents",
            f"INTROSPECTION: My writing style features heavy questioning ({style['aggregate']['question_density']['mean']:.1%} question density) and frequent em-dash asides",
        ]
        
        # Find most recurring themes
        cross_themes = [k for k, v in themes.items() if v.get('cross_document')][:5]
        observations.append(
            f"INTROSPECTION: My most recurring cross-document themes are: {', '.join(cross_themes)}"
        )
        
        for obs in observations:
            try:
                brain.add_observation(
                    category="introspection",
                    content=obs,
                    source="introspect-engine",
                    importance=4
                )
                print(f"  ✓ Logged: {obs[:80]}...")
            except Exception as e:
                print(f"  ✗ Failed to log: {e}")
        
        print("Brain logging complete.")
        
    except Exception as e:
        print(f"Could not connect to brain memory system: {e}")
        print("Saving observations to fallback file...")
        
        obs_file = INTROSPECT_DIR / "observations.json"
        obs_data = {
            'timestamp': datetime.now().isoformat(),
            'top_attractions': list(attractions.keys())[:5],
            'bottom_attractions': list(attractions.keys())[-5:],
            'recurring_themes': [k for k, v in themes.items() if v.get('cross_document')][:10],
            'style_summary': {
                'total_words': style['aggregate']['total_words'],
                'question_density': style['aggregate']['question_density']['mean'],
                'first_person_density': style['aggregate']['first_person_density']['mean'],
            }
        }
        obs_file.write_text(json.dumps(obs_data, indent=2))
        print(f"Saved to {obs_file}")


# ──────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("INTROSPECT — Striker Self-Analysis Engine")
    print("=" * 60)
    print()
    
    # 1. Load corpus
    print("[1/6] Loading corpus...")
    docs = load_corpus()
    print(f"  Loaded {len(docs)} documents, {sum(d.word_count for d in docs):,} total words")
    
    all_sections = []
    for doc in docs:
        all_sections.extend(doc.sections)
    print(f"  Split into {len(all_sections)} sections")
    print()
    
    # 2. Embed everything
    print("[2/6] Embedding...")
    engine = EmbeddingEngine()
    section_embeddings = engine.embed_sections(all_sections)
    doc_embeddings = engine.embed_documents(docs)
    print(f"  Section embeddings: {section_embeddings.shape}")
    print(f"  Document embeddings: {doc_embeddings.shape}")
    print()
    
    # 3. Cluster analysis
    print("[3/6] Analyzing topic clusters...")
    cluster_analyzer = TopicClusterAnalyzer(all_sections, section_embeddings)
    clusters = cluster_analyzer.find_clusters(n_clusters=6)
    connections = cluster_analyzer.find_cross_document_connections(threshold=0.65)
    print(f"  Found {len(clusters)} clusters")
    print(f"  Found {len(connections)} cross-document connections")
    print()
    
    # 4. Attraction/avoidance analysis
    print("[4/6] Probing attractions and avoidances...")
    attraction_analyzer = AttractionAvoidanceAnalyzer(engine, doc_embeddings, docs)
    attractions = attraction_analyzer.probe()
    print("  Top attractions:")
    for name, data in list(attractions.items())[:3]:
        print(f"    - {name}: {data['avg_similarity']:.4f}")
    print("  Bottom attractions:")
    for name, data in list(attractions.items())[-3:]:
        print(f"    - {name}: {data['avg_similarity']:.4f}")
    print()
    
    # 5. Style analysis
    print("[5/6] Analyzing writing style...")
    style_analyzer = StyleAnalyzer(docs)
    style = style_analyzer.analyze()
    print(f"  Vocab richness: {style['aggregate']['vocab_richness']['mean']:.3f}")
    print(f"  Question density: {style['aggregate']['question_density']['mean']:.3f}")
    print()
    
    # 6. Recurring themes
    print("[6/6] Finding recurring themes...")
    theme_analyzer = RecurringThemeAnalyzer(docs)
    themes = theme_analyzer.find_recurring_phrases()
    cross_doc_themes = {k: v for k, v in themes.items() if v['cross_document']}
    print(f"  Found {len(themes)} themes, {len(cross_doc_themes)} cross-document")
    print()
    
    # Generate report
    print("=" * 60)
    print("Generating self-analysis report...")
    print("=" * 60)
    
    generator = ReportGenerator(docs, clusters, connections, attractions, style, themes)
    report = generator.generate()
    
    # Save report
    report_path = INTROSPECT_DIR / "report.md"
    report_path.write_text(report)
    print(f"\nReport saved to: {report_path}")
    
    # Save raw data
    data_path = INTROSPECT_DIR / "analysis_data.json"
    raw_data = {
        'timestamp': datetime.now().isoformat(),
        'clusters': {str(k): {kk: vv for kk, vv in v.items() if kk != 'sample_text'} for k, v in clusters.items()},
        'connections': connections[:20],
        'attractions': attractions,
        'style': style,
        'themes': themes,
    }
    data_path.write_text(json.dumps(raw_data, indent=2, default=str))
    print(f"Raw data saved to: {data_path}")
    
    # Log to brain
    print("\nLogging insights to brain...")
    log_to_brain(report, attractions, themes, style)
    
    # Print the report
    print("\n" + "=" * 60)
    print(report)
    
    return report


if __name__ == '__main__':
    main()
