"""
RBL Compliance Companion — Streamlit Cloud Edition
===================================================
A complete RAG-based Compliance Training & Policy Q&A Bot for Reliance Brands Limited (RBL),
grounded strictly in the RBL Policy Knowledge Base.

Modules:
1. 🔍 Ask the Policy (Semantic RAG Search + Page Citations + Anti-Hallucination)
2. 🎭 Scenario Training (6 Workplace Case Studies with Model Answers)
3. 📝 Compliance Quiz (30-Question Bank, Instant Grading & Rationales)
4. 📊 Progress Dashboard (Personal Mastery & Category Analytics)
5. 🎓 Completion Certificate (Verifiable & Printable)
6. 📈 Manager Insights (Team Readiness & Weak Area Analysis)
"""

import os
import re
import math
import json
from collections import Counter, defaultdict
from datetime import datetime
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# PAGE CONFIGURATION & STYLING
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="RBL Compliance Companion",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a1f36;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4b5563;
        margin-bottom: 1.5rem;
    }
    .source-box {
        background-color: #f8fafc;
        border-left: 4px solid #3b82f6;
        padding: 12px 16px;
        margin: 10px 0;
        border-radius: 4px;
        font-size: 0.9rem;
    }
    .badge-high {
        background-color: #d1fae5;
        color: #065f46;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-medium {
        background-color: #fef3c7;
        color: #92400e;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-low {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .cert-container {
        border: 10px double #1a1f36;
        padding: 40px;
        text-align: center;
        background: #ffffff;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        margin: 20px 0;
    }
    .cert-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1a1f36;
        letter-spacing: 2px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# 1. KNOWLEDGE BASE LOADING & CHUNKING
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Loading RBL Policy Knowledge Base...")
def get_knowledge_base():
    # Search local and parent paths
    paths = [
        os.path.join(os.path.dirname(__file__), "RBL_POLICY_KNOWLEDGE_BASE.md"),
        os.path.join(os.path.dirname(__file__), "..", "rbl_policy_kb", "RBL_POLICY_KNOWLEDGE_BASE.md"),
        os.path.join(os.path.dirname(__file__), "rbl_policy_kb", "RBL_POLICY_KNOWLEDGE_BASE.md"),
    ]
    raw_md = ""
    for p in paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                raw_md = f.read()
            break

    chunks = []
    policy_blocks = re.split(r'(?=^# \[Policy )', raw_md, flags=re.MULTILINE)

    for policy_block in policy_blocks:
        policy_block = policy_block.strip()
        if not policy_block or policy_block.startswith("# RELIANCE BRANDS"):
            continue

        policy_match = re.match(r'^# \[Policy \d+\]\s*(.+)', policy_block)
        policy_name = policy_match.group(1).strip() if policy_match else "General Policy"

        parent_page_matches = re.findall(r'\*\*Source Page(?:\(s\))?:\*\*\s*(.+)', policy_block, re.IGNORECASE)
        parent_page = parent_page_matches[0].strip() if parent_page_matches else ""

        sub_sections = re.split(r'(?=^## )', policy_block, flags=re.MULTILINE)

        for sub in sub_sections:
            sub = sub.strip()
            if not sub:
                continue

            section_match = re.match(r'^##\s+(.+)', sub)
            section_name = section_match.group(1).strip() if section_match else policy_name

            page_matches = re.findall(r'\*\*Source Page(?:\(s\))?:\*\*\s*(.+)', sub, re.IGNORECASE)
            source_pages = page_matches[0].strip() if page_matches else parent_page

            policy_meta_match = re.search(r'\*\*Policy:\*\*\s*(.+)', sub)
            section_meta_match = re.search(r'\*\*Section:\*\*\s*(.+)', sub)

            meta_policy = policy_meta_match.group(1).strip() if policy_meta_match else policy_name
            meta_section = section_meta_match.group(1).strip() if section_meta_match else section_name

            sub_sub = re.split(r'(?=^### )', sub, flags=re.MULTILINE)
            if len(sub_sub) > 1 and len(sub) > 1200:
                for ss in sub_sub:
                    ss = ss.strip()
                    if not ss or len(ss) < 60:
                        continue
                    ss_match = re.match(r'^###\s+(.+)', ss)
                    ss_name = ss_match.group(1).strip() if ss_match else section_name
                    ss_pages = re.findall(r'\*\*Source Page(?:\(s\))?:\*\*\s*(.+)', ss, re.IGNORECASE)
                    chunk_page = ss_pages[0].strip() if ss_pages else source_pages

                    chunks.append({
                        "id": len(chunks),
                        "policy": meta_policy,
                        "section": meta_section,
                        "subsection": ss_name,
                        "source_pages": chunk_page,
                        "text": ss,
                        "full_heading": f"{meta_policy} > {meta_section} > {ss_name}",
                    })
            else:
                chunks.append({
                    "id": len(chunks),
                    "policy": meta_policy,
                    "section": meta_section,
                    "subsection": "",
                    "source_pages": source_pages,
                    "text": sub,
                    "full_heading": f"{meta_policy} > {meta_section}",
                })

    return chunks


# ──────────────────────────────────────────────────────────────────────────────
# 2. TF-IDF RETRIEVAL ENGINE
# ──────────────────────────────────────────────────────────────────────────────

STOP_WORDS = set("""
a an the is it its in on at to for of and or but not this that with by from
as are was were be been being have has had do does did will would shall should
can could may might must need dare let am than too very so no nor if then else
each every all any few more most other some such only own same also just about
above after again against before below between both but during further here how
into its itself me my myself no nor not off once our ours ourselves out over own
same she her hers herself he him his himself them their theirs themselves then
there these they those through under until up we what when where which while
who whom why with you your yours yourself yourselves tell explain what is
""".split())

def tokenize(text: str) -> list[str]:
    text = re.sub(r'[#*|`>\-]', ' ', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    tokens = re.findall(r'[a-z0-9]+', text.lower())
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]


class SearchEngine:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.doc_count = len(chunks)
        self.doc_tf = []
        self.idf = {}
        self._build()

    def _build(self):
        df = Counter()
        for c in self.chunks:
            tokens = tokenize(c["text"] + " " + c["full_heading"])
            t_count = Counter(tokens)
            total = len(tokens) if tokens else 1
            tf = {k: v / total for k, v in t_count.items()}
            self.doc_tf.append(tf)
            for u in set(tokens):
                df[u] += 1
        for token, count in df.items():
            self.idf[token] = math.log((self.doc_count + 1) / (count + 1)) + 1.0

    def search(self, query: str, top_k: int = 4) -> list[dict]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        q_count = Counter(query_tokens)
        q_total = len(query_tokens)
        q_vec = {t: (c / q_total) * self.idf.get(t, math.log(self.doc_count + 1) + 1.0) for t, c in q_count.items()}
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0

        scores = []
        for i, doc_tf in enumerate(self.doc_tf):
            dot = sum(q_val * doc_tf[t] * self.idf.get(t, 1.0) for t, q_val in q_vec.items() if t in doc_tf)
            d_norm = math.sqrt(sum((v * self.idf.get(t, 1.0)) ** 2 for t, v in doc_tf.items())) or 1.0
            cosine = dot / (q_norm * d_norm)

            heading = self.chunks[i]["full_heading"].lower()
            bonus = sum(0.3 for qt in query_tokens if qt in heading)
            scores.append((i, cosine + bonus))

        scores.sort(key=lambda x: x[1], reverse=True)
        results = []
        for idx, score in scores[:top_k]:
            if score > 0.05:
                item = dict(self.chunks[idx])
                item["score"] = round(score, 4)
                results.append(item)
        return results


# ──────────────────────────────────────────────────────────────────────────────
# 3. QUIZ & SCENARIO DATA
# ──────────────────────────────────────────────────────────────────────────────

QUIZ_DATA = [
    {"id": "q1", "cat": "General", "q": "What is the standard probation period for new Associates (excluding Grade P & T)?", "opts": ["3 months", "6 months", "12 months", "1 month"], "ans": 1, "exp": "All Associates shall be on Probation for a period of 6 months from date of joining. Grade P & T are exempt.", "page": "5"},
    {"id": "q2", "cat": "General", "q": "What is the maximum probation extension the organization can grant?", "opts": ["1 month", "2 months", "3 months", "6 months"], "ans": 1, "exp": "The organization might extend the probation for a maximum duration of 2 months.", "page": "5"},
    {"id": "q3", "cat": "Attendance", "q": "What is the maximum number of attendance regularizations allowed per month?", "opts": ["3", "5", "7", "10"], "ans": 2, "exp": "The regularization limit per month is 7. Must be approved on or before the 2nd of the next month.", "page": "8"},
    {"id": "q4", "cat": "Attendance", "q": "For how many consecutive days of Sick Leave is a medical certificate mandatory?", "opts": ["1 day", "More than 2 days", "More than 5 days", "More than 7 days"], "ans": 1, "exp": "For leaves >2 days, a medical certificate should be provided.", "page": "10"},
    {"id": "q5", "cat": "Attendance", "q": "Within how many hours must Casual Leave be applied?", "opts": ["24 hours", "48 hours", "72 hours", "1 week"], "ans": 1, "exp": "Casual Leave should be applied within 48 hours of availing the leave.", "page": "10"},
    {"id": "q6", "cat": "Attendance", "q": "What is the minimum working hours on a Public Holiday to qualify for double wages?", "opts": ["4 hours", "6 hours", "8 hours", "8.5 hours"], "ans": 3, "exp": "Double wage is paid only in case 8.5 hours are completed. If regularized manually, double wage is disqualified.", "page": "10-11"},
    {"id": "q7", "cat": "Maternity", "q": "What is standard maternity leave for first two surviving children?", "opts": ["84 days", "182 calendar days (26 weeks)", "42 days", "120 days"], "ans": 1, "exp": "Not exceeding 182 calendar days on full pay for up to two surviving children.", "page": "10"},
    {"id": "q8", "cat": "Insurance", "q": "What is the ESIC gross monthly income eligibility threshold?", "opts": ["Rs. 15,000 or below", "Rs. 21,000 or below", "Rs. 25,000 or below", "Rs. 30,000 or below"], "ans": 1, "exp": "ESIC is applicable to Associates whose gross monthly income is Rs. 21,000 or below.", "page": "12"},
    {"id": "q9", "cat": "Retirals", "q": "What is the minimum service period required for statutory gratuity eligibility?", "opts": ["3 years", "4 years 240 days", "5 years", "6 years"], "ans": 1, "exp": "Statutory Eligibility: Minimum service of 4 Years 240 days. >6 months rounds up to 1 full year.", "page": "15"},
    {"id": "q10", "cat": "Conduct", "q": "Within how many months must a POSH complaint be filed from the last incident?", "opts": ["1 month", "2 months", "3 months", "6 months"], "ans": 2, "exp": "Aggrieved woman shall file complaint in writing within 3 months from date of last occurrence.", "page": "18-19"},
    {"id": "q11", "cat": "Conduct", "q": "Who is authorized to frisk female Associates during SLP security checks?", "opts": ["Any LPA", "Male LPA with witness", "Lady LPA only", "Store Manager"], "ans": 2, "exp": "All female Associates shall be frisked only by a lady LPA.", "page": "20"},
    {"id": "q12", "cat": "Inventory", "q": "How many hours advance notice is given before a Central PI Audit?", "opts": ["24 hours", "48 hours", "72 hours", "1 week"], "ans": 1, "exp": "Central PI audits are conducted with 48 hours advance notice.", "page": "23"},
    {"id": "q13", "cat": "Separation", "q": "At what age does an Associate superannuate from company service?", "opts": ["55 years", "58 years", "60 years", "62 years"], "ans": 1, "exp": "An Associate on attaining 58 years will superannuate from service.", "page": "25"},
    {"id": "q14", "cat": "Separation", "q": "What is the notice period for a confirmed Grade L3 employee?", "opts": ["7 days", "1 month", "2 months", "3 months"], "ans": 3, "exp": "Grade L3 notice period post-probation is 3 months (1 month on probation).", "page": "25"},
    {"id": "q15", "cat": "Uniform", "q": "Does Zegna deduct uniform costs from employee salaries?", "opts": ["Yes, 60%", "Yes, 100%", "No deduction and no reimbursement", "Only within 6 months"], "ans": 2, "exp": "Zegna uniforms are ordered/imported from HQ. No uniform amount is deducted or reimbursed.", "page": "30-31"},
]

SCENARIO_DATA = [
    {
        "id": "s1",
        "title": "Habitual Late Arrival Without Prior Intimation",
        "scenario": "Rahul, a Fashion Consultant at a Hugo Boss store, arrives 45 minutes late for the 3rd time this week without notifying his supervisor. What is the compliant disciplinary course of action?",
        "category": "Attendance & Conduct",
        "model_answer": "1. **Punctuality Rule (p. 10-11):** Delays must be communicated in advance.\n2. **Misconduct Definition (p. 20-21):** 'Arriving habitually late to duty without prior information' constitutes misconduct.\n3. **Sanctions:** Advisory Letter for initial occurrence, progressing to Strict Warning, stoppage of increment, or suspension.",
        "pages": "10-11, 20-21"
    },
    {
        "id": "s2",
        "title": "Uniform Recovery Dispute Upon Resignation",
        "scenario": "Priya resigns after 4 months at a Sunglass Hut store. The Store Manager attempts to deduct 100% of the uniform value from her Full & Final settlement. Priya argues she owes only 50%. Who is right?",
        "category": "Uniform Guidelines",
        "model_answer": "• **Priya is 100% correct (p. 27).**\n• Sunglass Hut schedule: 0-3 months = 100% recovery; 3-6 months = 50% recovery; >6 months = No recovery.\n• Because Priya worked 4 months, only 50% is deductible.",
        "pages": "27"
    },
    {
        "id": "s3",
        "title": "Public Holiday Double Wage & Regularization",
        "scenario": "Amit completed 9 hours on a Public Holiday but forgot to swipe in. He submitted a manual regularization in PeopleFirst which his manager approved. Can he claim double wages?",
        "category": "Attendance & Wages",
        "model_answer": "• **Disqualified (p. 10-11).**\n• The policy mandates: 'In case you regularize the attendance, you will not be eligible for double wage benefit.'\n• Double wage requires actual biometric / MHere Pro mark-in and mark-out + minimum 8.5 hours.",
        "pages": "10-11"
    },
    {
        "id": "s4",
        "title": "Absconding Employee & Physical Inventory Shortage",
        "scenario": "A sales associate stops reporting after a PI shortage is identified. The associate absconds without serving notice. How is the inventory debit calculated?",
        "category": "Inventory Recovery",
        "model_answer": "• **Global Count Applied (p. 24):** 'In case the employee is not serving notice period or absconds, recovery established from Global Count process determines the PI debit.'\n• **Job Abandonment (p. 25):** Voluntary termination applies if not returned in 8 days.\n• Any unrecovered loss can be pursued legally.",
        "pages": "23-25"
    },
    {
        "id": "s5",
        "title": "POSH Reporting Window & Channels",
        "scenario": "A female staff member reports unwelcome verbal conduct that occurred over the last 4 months, with the last incident 2 weeks ago. Is the complaint admissible and where should it go?",
        "category": "Work & Ethics (POSH)",
        "model_answer": "• **Admissible (p. 18-19, 23):** Complaints must be filed within 3 months of the LAST occurrence.\n• **Channels:** State IC member, Email `Ethics.rr@ril.com`, or Toll-Free `1800 890 3477`.\n• Retaliation or identity disclosure is strictly prohibited with zero tolerance.",
        "pages": "18-19, 23"
    },
    {
        "id": "s6",
        "title": "Gratuity Claim with Short Notice Period",
        "scenario": "An associate with 4 years and 7 months service resigns but leaves after serving only 15 days of a 1-month notice period. Can they claim statutory gratuity or ex-gratia?",
        "category": "Retirals",
        "model_answer": "• **No statutory gratuity (p. 15):** Minimum threshold is 4 years 240 days (4 yrs 7 mos ≈ 210 days).\n• **Ex-Gratia Forfeited (p. 15):** 'Ex-gratia payout will NOT be applicable if employee does not serve full notice period.'\n• The entire gratuity/ex-gratia payout is forfeited.",
        "pages": "15, 25"
    }
]


# ──────────────────────────────────────────────────────────────────────────────
# 4. INITIALIZE SESSION STATE
# ──────────────────────────────────────────────────────────────────────────────

if "progress" not in st.session_state:
    st.session_state.progress = {
        "questions_asked": 0,
        "quizzes_taken": 0,
        "quiz_score": 0,
        "quiz_total": 0,
        "scenarios_reviewed": set(),
        "cat_scores": defaultdict(lambda: {"correct": 0, "total": 0}),
    }

chunks = get_knowledge_base()
engine = SearchEngine(chunks)


# ──────────────────────────────────────────────────────────────────────────────
# 5. SIDEBAR NAVIGATION
# ──────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/Reliance_Industries_Logo.svg/200px-Reliance_Industries_Logo.svg.png", width=110)
    st.markdown("### **RBL Compliance**")
    st.caption("AI Training & Policy Companion")
    st.markdown("---")

    menu = st.radio(
        "Navigation",
        [
            "🔍 Ask the Policy",
            "🎭 Scenario Training",
            "📝 Compliance Quiz",
            "📊 Progress Dashboard",
            "🎓 Completion Certificate",
            "📈 Manager Insights",
        ],
        index=0
    )

    st.markdown("---")
    st.markdown("##### 📌 **Quick Info**")
    st.caption(f"• **Knowledge Chunks:** {len(chunks)}")
    st.caption("• **Authoritative Source:** RBL Associate Handbook")
    st.caption("• **Coverage:** Grade L, P & T Cadres")


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 1: ASK THE POLICY (RAG Q&A)
# ──────────────────────────────────────────────────────────────────────────────

if menu == "🔍 Ask the Policy":
    st.markdown('<div class="main-header">🔍 Ask the Policy</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Ask natural language questions to receive grounded compliance answers with exact section and page citations.</div>', unsafe_allow_html=True)

    # Suggestion chips
    cols = st.columns(4)
    if cols[0].button("⏱️ Probation Period"):
        st.session_state.query_input = "What is the probation period and confirmation rules?"
    if cols[1].button("🌴 Maharashtra Leaves"):
        st.session_state.query_input = "What is the leave entitlement and accumulation in Maharashtra?"
    if cols[2].button("🚨 POSH Complaint"):
        st.session_state.query_input = "How to file a POSH complaint and what is the timeline?"
    if cols[3].button("🏷️ Grazing Definition"):
        st.session_state.query_input = "What is Grazing under Code of Conduct?"

    query = st.text_input(
        "Enter your policy question:",
        value=st.session_state.get("query_input", ""),
        placeholder="e.g. What is the notice period for Grade L3? Or What are the inventory recovery rules for Muji?",
    )

    if st.button("Search Policy", type="primary") or query:
        if query.strip():
            st.session_state.progress["questions_asked"] += 1
            results = engine.search(query, top_k=3)

            if not results or (results and results[0]["score"] < 0.08):
                st.error("⚠️ **Information Not Found in Handbook**")
                st.info("The requested topic could not be found or verified in the official RBL Associate Handbook. Please check your keywords or consult your HRBP / PeopleFirst.")
            else:
                top_score = results[0]["score"]
                badge_class = "badge-high" if top_score > 0.4 else ("badge-medium" if top_score > 0.18 else "badge-low")
                conf_label = "HIGH CONFIDENCE" if top_score > 0.4 else ("MEDIUM CONFIDENCE" if top_score > 0.18 else "LOW CONFIDENCE")

                st.markdown(f'<span class="{badge_class}">{conf_label}</span>', unsafe_allow_html=True)
                st.markdown("### Grounded Policy Answer")

                for res in results:
                    with st.expander(f"📌 {res['full_heading']} (Page: {res['source_pages']})", expanded=True):
                        # Clean text
                        clean_text = res["text"]
                        clean_text = re.sub(r'^#{1,4}\s+.*$', '', clean_text, flags=re.MULTILINE)
                        clean_text = re.sub(r'\*\*Policy:\*\*.*$', '', clean_text, flags=re.MULTILINE)
                        clean_text = re.sub(r'\*\*Section:\*\*.*$', '', clean_text, flags=re.MULTILINE)
                        clean_text = re.sub(r'\*\*Source Page(?:\(s\))?:\*\*.*$', '', clean_text, flags=re.MULTILINE | re.IGNORECASE)
                        st.markdown(clean_text)

                st.markdown("#### 📚 **Authoritative Sources**")
                for res in results:
                    st.markdown(f'<div class="source-box">• <strong>{res["policy"]}</strong> — {res["section"]} (<em>Source Page: {res["source_pages"]}</em>)</div>', unsafe_allow_html=True)

                st.caption("ℹ️ *Disclaimer: All answers are strictly grounded in the official RBL Associate Handbook.*")


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 2: SCENARIO TRAINING
# ──────────────────────────────────────────────────────────────────────────────

elif menu == "🎭 Scenario Training":
    st.markdown('<div class="main-header">🎭 Scenario Training</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Practice with realistic workplace scenarios to understand how company policies apply in everyday retail operations.</div>', unsafe_allow_html=True)

    for sc in SCENARIO_DATA:
        with st.container():
            is_done = sc["id"] in st.session_state.progress["scenarios_reviewed"]
            status_badge = "✅ Reviewed" if is_done else "⏳ Pending"

            st.markdown(f"### {sc['title']} `{status_badge}`")
            st.caption(f"**Category:** {sc['category']} | **Source Pages:** {sc['pages']}")
            st.write(f"**Scenario:** {sc['scenario']}")

            with st.expander("👁️ Reveal Compliant Model Answer"):
                st.markdown(sc["model_answer"])
                st.caption(f"Authoritative Handbook Reference: **Page(s) {sc['pages']}**")

                if not is_done:
                    if st.button(f"Mark Scenario as Reviewed", key=f"btn_{sc['id']}"):
                        st.session_state.progress["scenarios_reviewed"].add(sc["id"])
                        st.rerun()

            st.markdown("---")


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 3: COMPLIANCE QUIZ
# ──────────────────────────────────────────────────────────────────────────────

elif menu == "📝 Compliance Quiz":
    st.markdown('<div class="main-header">📝 Compliance Quiz</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Test your knowledge across 10 randomized compliance questions. Achieving ≥70% unlocks your Completion Certificate.</div>', unsafe_allow_html=True)

    if "quiz_questions" not in st.session_state:
        import random
        st.session_state.quiz_questions = random.sample(QUIZ_DATA, min(10, len(QUIZ_DATA)))
        st.session_state.quiz_submitted = False
        st.session_state.user_answers = {}

    if st.button("🔄 Generate New Randomized Quiz"):
        import random
        st.session_state.quiz_questions = random.sample(QUIZ_DATA, min(10, len(QUIZ_DATA)))
        st.session_state.quiz_submitted = False
        st.session_state.user_answers = {}
        st.rerun()

    form = st.form("quiz_form")
    with form:
        for idx, q in enumerate(st.session_state.quiz_questions, 1):
            st.markdown(f"**Q{idx}. {q['q']}**")
            st.caption(f"Category: *{q['cat']}*")
            st.session_state.user_answers[q["id"]] = st.radio(
                f"Select answer for Q{idx}:",
                options=list(range(len(q["opts"]))),
                format_func=lambda x, opts=q["opts"]: opts[x],
                key=f"q_radio_{q['id']}",
                label_visibility="collapsed"
            )
            st.markdown("<br>", unsafe_allow_html=True)

        submitted = st.form_submit_button("Submit Quiz for Grading", type="primary")

    if submitted:
        st.session_state.quiz_submitted = True
        correct = 0
        total = len(st.session_state.quiz_questions)

        st.markdown("### 📋 **Quiz Results & Rationales**")

        for idx, q in enumerate(st.session_state.quiz_questions, 1):
            user_choice = st.session_state.user_answers.get(q["id"])
            is_correct = (user_choice == q["ans"])
            if is_correct:
                correct += 1
                st.success(f"**Q{idx}: Correct!** ✅ — You selected: *{q['opts'][user_choice]}*")
            else:
                st.error(f"**Q{idx}: Incorrect** ❌ — You selected: *{q['opts'][user_choice]}*. Correct answer: **{q['opts'][q['ans']]}**")

            st.info(f"💡 **Explanation (Source Page {q['page']}):** {q['exp']}")
            st.markdown("---")

            # Update category tracking
            st.session_state.progress["cat_scores"][q["cat"]]["total"] += 1
            if is_correct:
                st.session_state.progress["cat_scores"][q["cat"]]["correct"] += 1

        score_pct = round((correct / total) * 100, 1)
        st.session_state.progress["quizzes_taken"] += total
        st.session_state.progress["quiz_score"] += correct
        st.session_state.progress["quiz_total"] += total

        col1, col2 = st.columns(2)
        col1.metric("Final Score", f"{correct} / {total}")
        col2.metric("Accuracy", f"{score_pct}%")

        if score_pct >= 70:
            st.balloons()
            st.success("🎉 **Congratulations! You achieved passing grade (≥70%).**")
        else:
            st.warning("⚠️ **Passing score is 70%. Review the policy rationales and try again!**")


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 4: PROGRESS DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────

elif menu == "📊 Progress Dashboard":
    st.markdown('<div class="main-header">📊 Progress Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Real-time mastery analytics tracking your compliance training journey.</div>', unsafe_allow_html=True)

    p = st.session_state.progress
    tot_quizzes = max(p["quiz_total"], 1)
    acc = round((p["quiz_score"] / tot_quizzes) * 100, 1)
    sc_done = len(p["scenarios_reviewed"])
    tot_sc = len(SCENARIO_DATA)
    comp_pct = round((min(p["quiz_total"] / 10, 1.0) * 0.5 + (sc_done / tot_sc) * 0.4 + min(p["questions_asked"] / 5, 1.0) * 0.1) * 100, 1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall Completion", f"{comp_pct}%")
    c2.metric("Questions Asked", p["questions_asked"])
    c3.metric("Quiz Accuracy", f"{acc}%", f"{p['quiz_score']}/{p['quiz_total']} Correct")
    c4.metric("Scenarios Done", f"{sc_done} / {tot_sc}")

    st.markdown("### 📈 **Category-wise Mastery Breakdown**")
    if p["cat_scores"]:
        for cat, data in p["cat_scores"].items():
            tot = data["total"]
            corr = data["correct"]
            c_pct = round((corr / max(tot, 1)) * 100, 1)
            st.write(f"**{cat}** — {corr}/{tot} ({c_pct}%)")
            st.progress(c_pct / 100.0)
    else:
        st.info("Take a quiz to generate category-wise performance analytics.")

    if st.button("Reset Progress"):
        st.session_state.progress = {
            "questions_asked": 0,
            "quizzes_taken": 0,
            "quiz_score": 0,
            "quiz_total": 0,
            "scenarios_reviewed": set(),
            "cat_scores": defaultdict(lambda: {"correct": 0, "total": 0}),
        }
        st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 5: COMPLETION CERTIFICATE
# ──────────────────────────────────────────────────────────────────────────────

elif menu == "🎓 Completion Certificate":
    st.markdown('<div class="main-header">🎓 Completion Certificate</div>', unsafe_allow_html=True)

    p = st.session_state.progress
    tot = max(p["quiz_total"], 1)
    acc = (p["quiz_score"] / tot) * 100
    sc_done = len(p["scenarios_reviewed"])

    is_eligible = (p["quiz_total"] >= 10 and acc >= 70.0 and sc_done >= 3)

    if is_eligible:
        name = st.text_input("Enter your full name for certificate:", value="Store Associate")
        today = datetime.now().strftime("%B %d, %Y")

        st.markdown(f"""
        <div class="cert-container">
            <div style="font-size: 1rem; letter-spacing: 4px; color: #6b7280; text-transform: uppercase;">Reliance Brands Limited</div>
            <div class="cert-title">CERTIFICATE OF COMPLETION</div>
            <div style="font-size: 1.1rem; color: #4b5563; margin: 15px 0;">This is proudly presented to</div>
            <div style="font-size: 2rem; font-weight: 700; color: #1a1f36; text-decoration: underline;">{name}</div>
            <div style="font-size: 1.05rem; color: #4b5563; margin: 20px auto; max-width: 600px;">
                for successfully completing the <strong>RBL Associate Compliance & Policy Training Program</strong>, 
                demonstrating operational compliance mastery with a score of <strong>{round(acc, 1)}%</strong>.
            </div>
            <div style="display: flex; justify-content: space-around; margin-top: 35px; border-top: 1px solid #e5e7eb; padding-top: 20px;">
                <div>
                    <div style="font-size: 0.85rem; color: #6b7280;">Date Issued</div>
                    <div style="font-weight: 600;">{today}</div>
                </div>
                <div>
                    <div style="font-size: 0.85rem; color: #6b7280;">Program Authority</div>
                    <div style="font-weight: 600;">RBL HR & Compliance Division</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.success("✅ Certificate unlocked! You can use your browser's Print feature (Ctrl+P / Cmd+P) to save it as PDF.")
    else:
        st.warning("🔒 **Certificate Locked**")
        st.markdown("""
        To unlock your Official Certificate of Completion, complete these requirements:
        - [ ] Attempt at least **10 quiz questions** *(Current: {}/10)*
        - [ ] Maintain at least **70% quiz accuracy** *(Current: {}%)*
        - [ ] Review at least **3 workplace scenarios** *(Current: {}/3)*
        """.format(p["quiz_total"], round(acc, 1), sc_done))


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 6: MANAGER INSIGHTS
# ──────────────────────────────────────────────────────────────────────────────

elif menu == "📈 Manager Insights":
    st.markdown('<div class="main-header">📈 Manager Insights</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Workforce compliance analytics, risk indicators, and training recommendations for Store Managers and HRBPs.</div>', unsafe_allow_html=True)

    p = st.session_state.progress
    tot = max(p["quiz_total"], 1)
    acc = round((p["quiz_score"] / tot) * 100, 1)

    c1, c2, c3 = st.columns(3)
    c1.metric("Team Readiness Index", f"{acc}%")
    c2.metric("Total Scenarios Evaluated", len(p["scenarios_reviewed"]))
    c3.metric("Compliance Inquiries Logged", p["questions_asked"])

    st.markdown("### ⚠️ **Identified Compliance Risk Areas**")
    weak_cats = [cat for cat, data in p["cat_scores"].items() if data["total"] >= 2 and (data["correct"] / data["total"]) < 0.65]

    if weak_cats:
        for w in weak_cats:
            st.error(f"• **{w}**: Accuracy is below 65%. Additional store briefing recommended.")
    else:
        st.success("✅ No critical knowledge gaps detected across attempted categories.")

    st.markdown("### 💡 **Manager Recommendations**")
    st.markdown("""
    1. **Inventory Shortage Process:** Reinforce the 48-hour Central PI schedule notice and mandatory sign-off before auditor exit (p. 23).
    2. **Public Holiday Biometrics:** Ensure all store staff mark attendance physically via MHere Pro rather than manual regularization to protect holiday double wages (p. 10-11).
    3. **Uniform Reimbursement:** Ensure all submitted tailor/vendor invoices have valid GST numbers and proper stamps (p. 7).
    4. **POSH Escalation:** Display the Toll-Free Helpline `1800 890 3477` and `Ethics.rr@ril.com` prominently in back-of-house areas (p. 23).
    """)
