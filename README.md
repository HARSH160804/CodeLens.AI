# CodeLens

> AI-powered codebase understanding tool that transforms how developers and students explore unfamiliar code

[![AWS](https://img.shields.io/badge/AWS-Serverless-orange?logo=amazon-aws)](https://aws.amazon.com/)
[![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-blue?logo=amazon-aws)](https://aws.amazon.com/bedrock/)
[![React](https://img.shields.io/badge/React-18-blue?logo=react)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue?logo=typescript)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.9-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

##  Hackathon Submission Details

- **Team Name:** Old Monkey
- **Team Members:** Harsh Amarnani, Suryanshi Singh, Aditya Malik
- **Track:** Track 4 - AI for learning and developer productivity

---

## Overview

CodeLens is an intelligent codebase analysis platform that leverages Amazon Bedrock foundation models to help developers and students understand unfamiliar code repositories in minutes instead of hours. Built on AWS serverless architecture, it provides instant architecture insights, AI-generated documentation, and interactive Q&A capabilities.

### Key Features

- **AI-Powered Analysis** - Uses Amazon Bedrock (Nova lite) for semantic code understanding
- **Architecture Visualization** - Auto-generated Mermaid diagrams showing system structure
- **Interactive Q&A** - RAG-based chat interface for codebase questions
- **Documentation Generation** - Automatic README, API docs, and getting-started guides
- **Technology Detection** - Identifies frameworks, libraries, and architectural patterns
- **Async Processing** - SQS-based job queue for handling large repositories
- **Confidence Scoring** - AI-powered confidence metrics for analysis results
- **Multi-Language Support** - Python, JavaScript, TypeScript, Java, Go

---

## Use Cases

| User Type | Use Case |
|-----------|----------|
| **Students** | Learn from real-world codebases with AI-guided explanations |
| **New Team Members** | Onboard quickly without constant mentorship |
| **Open Source Contributors** | Navigate large projects independently |
| **Hackathon Participants** | Understand starter templates rapidly |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AWS Amplify                          │
│                  (React Frontend)                       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  API Gateway                            │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Lambda     │  │   Lambda     │  │   Lambda     │
│  Functions   │  │  Functions   │  │  Functions   │
│   (13)       │  │   (13)       │  │   (13)       │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  DynamoDB    │  │  Amazon      │  │     SQS      │
│  Tables (6)  │  │  Bedrock     │  │  Queues (2)  │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Tech Stack

**Frontend:**
- React 18 + TypeScript
- Tailwind CSS
- Vite
- React Router

**Backend:**
- Python 3.9
- AWS Lambda
- Amazon Bedrock (Claude 3.5 Sonnet)
- Amazon DynamoDB
- Amazon SQS
- Amazon S3

**Infrastructure:**
- AWS SAM (Serverless Application Model)
- AWS Amplify
- CloudFormation

---

## Quick Start

### Prerequisites

- AWS Account with Bedrock access
- Node.js 18+
- Python 3.9+
- AWS CLI v2
- AWS SAM CLI

### 1. Clone Repository

```bash
git clone https://github.com/HARSH160804/CodeLens.git
cd CodeLens
```

### 2. Deploy Backend

```bash
cd infrastructure
./deploy.sh
```

This will:
- Build Lambda functions
- Deploy to AWS (stack: `h2s-backend`)
- Create DynamoDB tables, SQS queues, and S3 buckets
- Output API Gateway endpoint

### 3. Deploy Frontend

**Option A: AWS Amplify Console (Recommended)**

1. Open [AWS Amplify Console](https://console.aws.amazon.com/amplify)
2. Click "New app" → "Host web app"
3. Connect your GitHub repository
4. Select branch: `main`
5. Amplify auto-detects configuration from `amplify.yml`
6. Deploy!

**Option B: Local Development**

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## Documentation

| Document | Description |
|----------|-------------|
| [Design Document](design.md) | System architecture and design decisions |
| [Requirements](requirements.md) | Functional and non-functional requirements |
| [Deployment Guide](AMPLIFY_DEPLOYMENT_GUIDE.md) | Complete deployment instructions |
| [Quick Deploy](DEPLOY_NOW.md) | 3-step deployment guide |

---

## Usage

### Analyze a Repository

1. **Enter GitHub URL**
   ```
   https://github.com/username/repository
   ```

2. **Wait for Processing**
   - Cloning repository
   - Analyzing code structure
   - Generating embeddings
   - Creating architecture diagram

3. **Explore Results**
   - View architecture visualization
   - Read AI-generated documentation
   - Ask questions via chat
   - Export documentation

### Example Queries

```
"What is the main purpose of this codebase?"
"How does authentication work?"
"Explain the data flow in this application"
"What architectural patterns are used?"
```

---

## Configuration

### Environment Variables

**Frontend** (`frontend/.env`):
```env
VITE_API_BASE_URL=https://your-api-gateway-url.amazonaws.com/Prod/
```

**Backend** (Set via SAM template):
- `SESSIONS_TABLE` - DynamoDB sessions table
- `REPOSITORIES_TABLE` - DynamoDB repositories table
- `EMBEDDINGS_TABLE` - DynamoDB embeddings table
- `CODE_BUCKET` - S3 bucket for artifacts
- `BEDROCK_REGION` - AWS region for Bedrock

---

## Testing

### Backend Tests

```bash
cd backend
python -m pytest tests/
```

### Frontend Tests

```bash
cd frontend
npm run test
```

### Integration Tests

```bash
# Test API endpoints
./dev-notes/test_api_endpoints.sh

# Test async ingestion
cd backend/tests
./run_async_tests.sh
```

---

## Features in Detail

### 1. Architecture Analysis

- **Technology Detection**: Automatically identifies frameworks, libraries, and tools
- **Pattern Recognition**: Detects MVC, microservices, monolith patterns
- **Dependency Mapping**: Visualizes module relationships
- **Confidence Scoring**: AI-powered confidence metrics for analysis accuracy

### 2. Documentation Generation

- **README Generation**: Auto-generated project overview
- **API Documentation**: Endpoint documentation with examples
- **Getting Started Guide**: Setup and usage instructions
- **Export Formats**: Markdown, PDF

### 3. Interactive Chat

- **RAG-Based**: Retrieval-Augmented Generation for accurate answers
- **Context-Aware**: Maintains conversation history
- **Code Citations**: References specific files and line numbers
- **Follow-up Suggestions**: AI-generated related questions

### 4. Async Processing

- **SQS Queue**: Handles large repositories without timeouts
- **Progress Tracking**: Real-time status updates
- **Idempotency**: Prevents duplicate processing
- **Error Handling**: Automatic retries with dead-letter queue

---

## Cost Estimate

Based on moderate usage (100 repos/day):

| Service | Monthly Cost |
|---------|--------------|
| Lambda | ~$15 |
| DynamoDB | ~$5 |
| S3 | ~$1 |
| SQS | ~$0.10 |
| Bedrock | ~$50 |
| API Gateway | ~$3 |
| Amplify | ~$13 |
| **Total** | **~$87/month** |

---

## Development

### Project Structure

```
CodeLens/
├── backend/                # Backend Lambda functions
│   ├── handlers/          # API route handlers
│   ├── lib/               # Core libraries
│   ├── services/          # Business logic
│   └── tests/             # Backend tests
├── frontend/              # React frontend
│   ├── public/            # Static assets
│   └── src/               # Source code
│       ├── components/    # React components
│       ├── hooks/         # Custom hooks
│       ├── pages/         # Page components
│       └── services/      # API services
├── infrastructure/        # AWS SAM templates
│   ├── template.yaml      # CloudFormation template
│   └── deploy.sh          # Deployment script
├── dev-notes/             # Development documentation
├── design.md              # System design
└── requirements.md        # Requirements
```

### Adding New Features

1. Create feature spec in `.kiro/specs/`
2. Implement backend handler in `backend/handlers/`
3. Add frontend component in `frontend/src/`
4. Update SAM template in `infrastructure/template.yaml`
5. Deploy with `./infrastructure/deploy.sh`

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow existing code style
- Add tests for new features
- Update documentation
- Ensure all tests pass

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Contact

**Project Maintainer:** Harsh Amarnani

**GitHub:** [@HARSH160804](https://github.com/HARSH160804)

**Repository:** [CodeLens](https://github.com/HARSH160804/CodeLens)

---

<div align="center">

**Built with love using AWS and Amazon Bedrock**

[Report Bug](https://github.com/HARSH160804/CodeLens/issues) · [Request Feature](https://github.com/HARSH160804/CodeLens/issues) · [Documentation](design.md)

</div>
