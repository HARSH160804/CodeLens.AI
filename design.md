# CodeLens — System Design Document

> **Track:** AI for Learning & Developer Productivity  
> **Version:** 1.0  
> **Date:** January 25, 2026

---

## 1. System Overview

CodeLens is an AI-powered system that transforms the way developers and students understand unfamiliar codebases. The system ingests source code repositories, processes them through multiple analysis stages, and leverages Amazon Bedrock foundation models to generate human-readable explanations, architecture summaries, and contextual answers to user questions. The system is deployed on AWS infrastructure using managed services for scalability, reliability, and serverless operation.

### Design Principles

| Principle | Description |
|-----------|-------------|
| **AI-Native** | Amazon Bedrock foundation models are central to the product, not an afterthought |
| **Semantic Over Syntactic** | Focus on understanding intent, not just structure |
| **Conversational** | Natural language as the primary interaction paradigm |
| **Progressive Disclosure** | Start with high-level views, allow drill-down |
| **Privacy-First** | Minimize data retention, support private repositories |
| **AWS-Managed** | Leverage AWS managed services for scalability and reduced operational overhead |

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
│                    (Web Application - AWS Amplify)                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AMAZON API GATEWAY                                   │
│                         (REST API Endpoints)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
         ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
         │  CODE PROCESSING │ │   AI REASONING   │ │    RESPONSE      │
         │     ENGINE       │ │      LAYER       │ │    GENERATOR     │
         │ (Lambda/ECS)     │ │ (Lambda/ECS)     │ │ (Lambda/ECS)     │
         └──────────────────┘ └──────────────────┘ └──────────────────┘
                    │                 │                 │
                    ▼                 ▼                 ▼
         ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
         │   Vector Store   │ │ Amazon Bedrock   │ │   Amazon S3      │
         │  (OpenSearch or  │ │ (Foundation      │ │ (Artifacts &     │
         │   In-Memory)     │ │  Models)         │ │  Uploads)        │
         └──────────────────┘ └──────────────────┘ └──────────────────┘
                    │                                     │
                    ▼                                     ▼
         ┌──────────────────────────────────────────────────────────────┐
         │                    Amazon DynamoDB                            │
         │              (Sessions & Metadata Storage)                    │
         └──────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

```
User Request → API Gateway → Route to appropriate Lambda/ECS service
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
     [Ingest Repo]          [Ask Question]          [Explain File]
            │                       │                       │
            ▼                       ▼                       ▼
    Code Processing         AI Reasoning              AI Reasoning
    (Store in S3)          (Bedrock + RAG)           (Bedrock)
            │                       │                       │
            ▼                       ▼                       ▼
    Store Embeddings        Retrieve Context         Generate Explanation
    (Vector Store)         (Vector Store)            (Bedrock)
            │                       │                       │
            └───────────────────────┼───────────────────────┘
                                    ▼
                           Response Generator
                                    │
                                    ▼
                              User Response
```

---

## 3. Component Breakdown

### 3.1 User Interface

**Purpose:** Provide an intuitive, browser-based interface for codebase exploration and interaction.

| Element | Function |
|---------|----------|
| **Repository Input** | Accept GitHub URLs or file uploads |
| **File Navigator** | Tree-view of repository structure |
| **Code Viewer** | Syntax-highlighted source display |
| **Explanation Panel** | AI-generated summaries and explanations |
| **Explanation Level Selector** | Dropdown to choose beginner/intermediate/advanced (default: intermediate) |
| **Chat Interface** | Conversational Q&A with the codebase using RAG-style retrieval |
| **Architecture View** | Structured textual architecture summary with AI-generated Mermaid.js flowchart showing major components and high-level data flow |

**Key Characteristics:**
- Single-page application for responsiveness
- Split-pane layout (navigation + content + chat)
- Real-time progress indicators during processing
- Markdown rendering for formatted explanations

---

### 3.2 Backend API

**Purpose:** Orchestrate requests between the frontend and processing services; manage sessions and state.

**Infrastructure:** Amazon API Gateway with AWS Lambda or Amazon ECS for compute.

| Endpoint Category | Responsibility |
|-------------------|----------------|
| **Ingestion** | Accept repository sources, trigger processing pipeline |
| **Query** | Route questions to AI Reasoning Layer |
| **Retrieval** | Serve file contents, explanations, and architecture data |
| **Session** | Manage user sessions and conversation history |

**API Design Principles:**
- RESTful endpoints with JSON payloads
- Stateless request handling via API Gateway
- Async processing for long-running operations using Lambda or ECS
- Session state stored in Amazon DynamoDB
- Repository artifacts stored in Amazon S3

**Core Endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/repos/ingest` | Start repository ingestion |
| GET | `/repos/{id}/status` | Check ingestion progress |
| GET | `/repos/{id}/architecture` | Retrieve architecture summary |
| GET | `/repos/{id}/files/{path}?level={beginner\|intermediate\|advanced}` | Get file with explanation at specified level |
| POST | `/repos/{id}/chat` | Submit a question |

**Explanation Level Parameter:**

All endpoints that generate explanations accept an optional `explanation_level` parameter:

| Level | Target Audience | Prompt Strategy |
|-------|----------------|-----------------|
| `beginner` | CS students, junior developers | "Explain as if teaching a CS freshman" |
| `intermediate` | Developers familiar with common frameworks | "Assume familiarity with common frameworks" (default) |
| `advanced` | Senior developers, architects | "Focus on design trade-offs and patterns" |

---

### 3.3 Code Processing Engine

**Purpose:** Ingest repositories, parse source files, and prepare code for AI analysis.

**Infrastructure:** AWS Lambda or Amazon ECS for compute; Amazon S3 for storage; vector store (Amazon OpenSearch or in-memory).

```
Repository URL/Upload
         │
         ▼
┌─────────────────┐
│  Clone / Unzip  │ ──→ Store in Amazon S3
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  File Discovery │ ──→ Filter by supported languages
└─────────────────┘      Exclude binaries, dependencies
         │
         ▼
┌─────────────────┐
│  Code Parsing   │ ──→ Extract functions, classes, imports
└─────────────────┘      Identify structure and relationships
         │
         ▼
┌─────────────────┐
│    Chunking     │ ──→ Split into semantic units
└─────────────────┘      Respect function/class boundaries
         │
         ▼
┌─────────────────┐
│   Embedding     │ ──→ Generate vector representations
└─────────────────┘      (Amazon Bedrock embeddings)
         │
         ▼
┌─────────────────┐
│ Index & Store   │ ──→ Store in vector database
└─────────────────┘      (OpenSearch or in-memory)
```

**Key Responsibilities:**

| Stage | Function |
|-------|----------|
| **Clone/Extract** | Retrieve code from GitHub or uploaded archives |
| **Discovery** | Enumerate files, detect languages, filter irrelevant content |
| **Parsing** | Extract structural information (lightweight parsing) to identify entry points, imports, and basic code organization |
| **Chunking** | Divide code into LLM-digestible segments while preserving context |
| **Embedding** | Convert chunks to vector representations for similarity search |
| **Indexing** | Store embeddings and metadata for fast retrieval |

---

### 3.4 AI Reasoning Layer

**Purpose:** Apply Amazon Bedrock foundation models to understand, synthesize, and explain code semantically.

**Infrastructure:** AWS Lambda or Amazon ECS for orchestration; Amazon Bedrock for foundation model access; vector store for retrieval.

```
┌─────────────────────────────────────────────────────────────────┐
│                      AI REASONING LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Retrieval     │  │   Reasoning     │  │   Synthesis     │  │
│  │   (RAG)         │  │  (Bedrock)      │  │   (Output)      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│         │                    │                    │              │
│         ▼                    ▼                    ▼              │
│  Find relevant        Apply Bedrock to      Combine into        │
│  code chunks          understand and        coherent response   │
│  via similarity       reason about code                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Core Functions:**

| Function | Description |
|----------|-------------|
| **Context Retrieval** | Query vector store to find code chunks relevant to user's question |
| **Architecture Analysis** | Multi-pass Bedrock reasoning over repository structure, entry points, detected technologies, and summarized context to synthesize high-level understanding |
| **File Explanation** | Generate natural language description of file purpose and contents using Bedrock |
| **Q&A Processing** | Answer user questions using retrieved context + Bedrock reasoning (RAG-style) |
| **Pattern Detection** | Identify architectural patterns, conventions, and design decisions using Bedrock |
| **Diagram Generation** | Generate Mermaid.js flowchart text showing major components, module relationships, and high-level data flow using Bedrock |

**RAG (Retrieval-Augmented Generation) Pipeline:**

```
User Question
      │
      ▼
┌─────────────┐
│  Embed      │ ──→ Convert question to vector (Bedrock)
│  Question   │
└─────────────┘
      │
      ▼
┌─────────────┐
│  Retrieve   │ ──→ Find top-K similar code chunks
│  Context    │      (Vector store query)
└─────────────┘
      │
      ▼
┌─────────────┐
│  Construct  │ ──→ Combine: System Prompt + Context + Question
│  Prompt     │
└─────────────┘
      │
      ▼
┌─────────────┐
│ Bedrock Call│ ──→ Generate answer with citations
└─────────────┘
      │
      ▼
   Response
```

---

### 3.5 Response Generator

**Purpose:** Format and structure AI outputs for presentation to users.

| Responsibility | Description |
|----------------|-------------|
| **Formatting** | Convert raw LLM output to structured, readable format |
| **Citation Linking** | Attach file paths and line numbers to claims |
| **Markdown Rendering** | Format code blocks, lists, and emphasis |
| **Confidence Indication** | Flag uncertain or incomplete answers |
| **Follow-up Suggestions** | Generate related questions for exploration |

**Output Types:**

| Type | Content |
|------|---------|
| **Architecture Summary** | Structured textual overview (primary source of truth) with AI-generated Mermaid.js flowchart derived from the textual explanation |
| **File Explanation** | Purpose, key functions, relationships, complexity |
| **Q&A Answer** | Direct answer with citations and follow-ups, generated using RAG-style retrieval |
| **Documentation** | README, API docs, getting-started guides |

**Architecture View Output Format (MVP):**

The Architecture View delivers two complementary outputs:

1. **Textual Architecture Summary** (primary source of truth):
   - High-level project overview
   - List of major components/modules with descriptions
   - Identified architectural patterns (e.g., MVC, microservices)
   - Module relationships and dependencies
   - Entry points and configuration files

2. **Mermaid.js Architecture Flowchart** (visual support):
   - AI-generated Mermaid text rendered in the frontend
   - Shows major components and module-level relationships
   - Depicts high-level data flow
   - Conceptual and intended for understanding system structure
   - Not guaranteed to be fully precise or exhaustive
   - Excludes: UML diagrams, class-level or function-level details, detailed runtime or call-graph accuracy

---

## 4. Data Flow

### 4.1 Repository Ingestion Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  User    │───▶│  Clone   │───▶│  Parse   │───▶│  Chunk   │───▶│  Embed   │
│  Input   │    │  Repo    │    │  Files   │    │  Code    │    │  Vectors │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                                      │
                                                                      ▼
┌──────────┐    ┌──────────┐    ┌──────────┐                   ┌──────────┐
│  User    │◀───│ Display  │◀───│ Generate │◀──────────────────│  Store   │
│  Views   │    │ Summary  │    │ Summary  │                   │  Index   │
└──────────┘    └──────────┘    └──────────┘                   └──────────┘
```

### 4.2 Question Answering Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  User    │───▶│  Embed   │───▶│ Retrieve │───▶│ Construct│───▶│  Query   │
│ Question │    │  Query   │    │ Context  │    │  Prompt  │    │   LLM    │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                                      │
                                                                      ▼
┌──────────┐    ┌──────────┐    ┌──────────┐                   ┌──────────┐
│  User    │◀───│  Format  │◀───│   Add    │◀──────────────────│  Parse   │
│  Views   │    │ Response │    │Citations │                   │  Answer  │
└──────────┘    └──────────┘    └──────────┘                   └──────────┘
```

### 4.3 Data Persistence

| Data Type | Storage | Retention |
|-----------|---------|-----------|
| Repository metadata | Amazon DynamoDB | Until session expires |
| Repository artifacts | Amazon S3 | Session lifetime |
| Code embeddings | Vector store (OpenSearch or in-memory) | Session lifetime |
| Conversation history | Amazon DynamoDB (keyed by session ID) | Session lifetime |
| Generated summaries | Amazon DynamoDB or in-memory cache | 24 hours |
| User sessions | Amazon DynamoDB | 24 hours |

---

## 5. AI Usage Justification

### 5.1 Why Generative AI is Essential (Not Optional)

> **Core Premise:** Understanding code requires semantic reasoning that cannot be achieved through rule-based systems.

CodeLens uses Amazon Bedrock foundation models to deliver value that fundamentally transforms the user experience:

**User Value Delivered by AI:**

| Capability | User Benefit |
|------------|--------------|
| **Faster Onboarding** | Developers understand unfamiliar codebases in minutes instead of hours or days |
| **Visual Architecture Understanding** | AI-generated diagrams provide instant conceptual clarity of system structure |
| **Context-Aware Answers** | Questions are answered based on actual code, not generic documentation |
| **Adaptive Explanations** | Content tailored to user expertise level (beginner/intermediate/advanced) |
| **Cross-File Comprehension** | Understand relationships and data flow that span multiple files |

**Technical Comparison:**

| Capability | Rule-Based Approach | AI-Powered Approach (Bedrock) |
|------------|---------------------|-------------------------------|
| **Architecture Detection** | Pattern-match folder names ("controllers" → MVC) | Analyze actual data flow and separation of concerns |
| **Code Explanation** | Template-based docstrings | Context-aware, human-readable explanations |
| **Intent Inference** | Impossible | Understand what `process_data()` actually does |
| **Cross-File Reasoning** | Limited to explicit imports | Infer implicit relationships and patterns |
| **Natural Language Q&A** | Keyword matching only | True comprehension and synthesis |
| **Diagram Generation** | Static templates | AI-generated conceptual flowcharts from code analysis |

### 5.2 AI Integration Points

| Feature | AI Role (Amazon Bedrock) | Justification |
|---------|--------------------------|---------------|
| **Architecture Summary** | Synthesize understanding across 100s of files | No rule can generalize across arbitrary projects |
| **Architecture Diagram** | Generate Mermaid.js flowcharts from code structure | Visual synthesis requires semantic understanding |
| **File Explanation** | Explain purpose beyond what names suggest | Requires reading and understanding implementation |
| **Q&A** | Answer arbitrary natural language questions | Unbounded question space requires general intelligence |
| **Pattern Recognition** | Identify design patterns from code structure | Patterns are implicit, not labeled |
| **Documentation Generation** | Produce human-quality prose | Writing requires language fluency |

### 5.3 Why This Is Not Rule-Based Automation

```
RULE-BASED:
  IF folder == "models" THEN label = "Data Models"
  IF file.endswith("_controller") THEN label = "Controller"
  
LIMITATION: Fails on non-standard naming, misses intent, cannot explain WHY

AI-POWERED (Amazon Bedrock):
  Foundation model reads function bodies, understands data transformations,
  infers that "DataProcessor" class validates and transforms input,
  explains in natural language why each method exists,
  generates visual diagram showing data flow
  
CAPABILITY: Works on arbitrary code, explains intent, adapts to context,
            produces visual and textual understanding
```

---

## 6. Scalability Considerations

### 6.1 Scaling Challenges

| Challenge | Impact | Mitigation |
|-----------|--------|------------|
| **Large Repositories** | Ingestion time, storage costs | Progressive loading, prioritize key files |
| **Foundation Model Token Limits** | Cannot process entire repo at once | Intelligent chunking, hierarchical summarization |
| **Concurrent Users** | API rate limits, compute costs | Request queuing, result caching, AWS auto-scaling |
| **Embedding Costs** | API costs scale with repo size | Batch processing, cache embeddings in vector store |
| **AWS Service Quotas** | Lambda concurrency, API Gateway limits | Monitor quotas, request increases, use ECS for long tasks |

### 6.2 Optimization Strategies

**Caching Layer:**

| Cache Target | Strategy | Benefit |
|--------------|----------|---------|
| Embeddings | Persist in vector store per repository | Avoid re-computation |
| Architecture summaries | Cache in DynamoDB for 24 hours | Reduce Bedrock calls |
| File explanations | Cache in DynamoDB on first access | Instant repeat access |
| Q&A responses | Session-scoped cache in DynamoDB | Reduce duplicate queries |

**Processing Optimizations:**

| Strategy | Description |
|----------|-------------|
| **Lazy Loading** | Generate explanations on-demand, not upfront |
| **Hierarchical Summarization** | Summarize files → modules → system |
| **Streaming Responses** | Return partial results as Bedrock generates |
| **Background Processing** | Pre-compute likely next actions using Lambda |
| **Scoped Docstring Generation** | Generate docstrings only for top-level public functions when user explicitly requests (FR-5.5) |

### 6.3 Hackathon Scope Trade-offs

| Full Product | Hackathon MVP |
|--------------|---------------|
| Distributed processing with SQS/Step Functions | Single Lambda or ECS task processing |
| Persistent vector database (OpenSearch Service) | In-memory vector store or lightweight OpenSearch |
| Multi-region deployment | Single AWS region |
| Support for repositories with thousands of files | Optimized for repositories with hundreds of files |
| Deep static analysis | Lightweight structural parsing + AI reasoning |

**Deployment Strategy:**

The system is designed for deployment on AWS infrastructure using managed services:
- **Frontend**: AWS Amplify for hosting and CI/CD
- **API**: Amazon API Gateway for REST endpoints
- **Compute**: AWS Lambda for serverless functions; Amazon ECS for longer-running tasks
- **Storage**: Amazon S3 for artifacts; Amazon DynamoDB for metadata and sessions
- **AI**: Amazon Bedrock for foundation model access
- **Vector Store**: Amazon OpenSearch Service or in-memory store on compute instances

This architecture leverages AWS-managed services to minimize operational overhead and enable rapid deployment suitable for hackathon timelines.

---

## 7. Ethical & Responsible AI Considerations

### 7.1 Privacy & Data Handling

| Concern | Mitigation |
|---------|------------|
| **Code Exposure** | Session-based storage; auto-delete after 24 hours |
| **Sensitive Data in Code** | Warn users; do not persist credentials or secrets |
| **Third-Party LLM APIs** | Disclose that code is sent to external APIs |
| **Private Repositories** | OAuth tokens never logged; explicit consent required |

### 7.2 AI Transparency

| Concern | Mitigation |
|---------|------------|
| **Hallucination** | Always cite source files; indicate uncertainty |
| **Accuracy Limits** | Disclose that AI explanations may be incomplete |
| **Not a Replacement** | Position as learning aid, not authoritative source |

### 7.3 Fairness & Accessibility

| Concern | Mitigation |
|---------|------------|
| **Language Bias** | English-focused MVP; acknowledge limitation |
| **Skill Level Bias** | Adjustable explanation complexity |
| **Accessibility** | Follow web accessibility standards (WCAG) |

### 7.4 Responsible Use

| Concern | Mitigation |
|---------|------------|
| **Academic Integrity** | Designed for learning, not plagiarism |
| **Copyright** | Analyze code, do not reproduce verbatim |
| **Security Research** | Do not assist in finding exploits |

---

## 8. Future Enhancements

### 8.1 Short-Term (Post-Hackathon)

| Enhancement | Description | Priority |
|-------------|-------------|----------|
| **Enhanced Diagram Accuracy** | Improve diagram precision with deeper static analysis and validation | Medium |
| **VS Code Extension** | Bring CodeLens AI into the IDE | High |
| **More Languages** | Rust, C++, Ruby, PHP support | High |
| **Comparison Mode** | Diff two codebases or versions | Medium |

### 8.2 Medium-Term (3-6 Months)

| Enhancement | Description | Priority |
|-------------|-------------|----------|
| **Large Repository Support** | Scale to repositories with thousands of files through optimized processing | High |
| **Team Workspaces** | Shared exploration sessions | High |
| **Learning Paths** | Guided tours through codebases | Medium |
| **Custom Indexing** | User-defined focus areas | Medium |
| **API Access** | Programmatic access for integrations | Medium |

### 8.3 Long-Term (6-12 Months)

| Enhancement | Description | Priority |
|-------------|-------------|----------|
| **Real-Time Collaboration** | Multi-user exploration | High |
| **Code Generation** | Suggest changes based on understanding | Medium |
| **Offline Mode** | Local LLM for sensitive codebases | Low |
| **CI/CD Integration** | Auto-generate docs on commit | Medium |

---

## Appendix: Technology Recommendations

### Hackathon Stack (Recommended)

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | React + TypeScript | Fast development, rich ecosystem |
| **Frontend Hosting** | AWS Amplify | Managed hosting with CI/CD |
| **API Gateway** | Amazon API Gateway | Managed REST API with AWS integration |
| **Backend Compute** | AWS Lambda + Amazon ECS | Serverless for quick tasks; ECS for longer processing |
| **Storage** | Amazon S3 | Scalable object storage for repositories |
| **Database** | Amazon DynamoDB | Serverless NoSQL for sessions and metadata |
| **Vector Store** | In-memory or Amazon OpenSearch | Zero configuration (in-memory) or managed service |
| **Foundation Models** | Amazon Bedrock | Managed access to multiple foundation models |
| **Embeddings** | Amazon Bedrock (Titan Embeddings) | High quality, AWS-native |

### Production Stack (Future)

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Vector Store** | Amazon OpenSearch Service | Fully managed, scalable vector search |
| **Queue** | Amazon SQS + AWS Step Functions | Distributed job processing and orchestration |
| **Monitoring** | Amazon CloudWatch | Integrated AWS monitoring and logging |
| **CDN** | Amazon CloudFront | Global content delivery |

---

*System design document prepared for hackathon submission — Old Monkey AI Team*
