# Project Documentation: Product Chatbot SDK Backend

---

## 1. Project Overview & Introduction

### What the Tool Does
A backend API for an AI-powered product chatbot, designed for e-commerce platforms. It answers product-related queries, provides product details, and supports advanced filtering and search.

### Core Purpose
- Enable conversational product support for users.
- Integrate AI (OpenAI, Gemini) for dynamic, context-aware responses.
- Centralize product, category, and question data for scalable support.

### High-Level Problem Solved
- Reduces manual support workload.
- Improves customer experience with instant, accurate answers.
- Supports product discovery and decision-making.

---

## 2. Technical Stack

### Backend Technologies
- Python 3.11
- FastAPI (REST API framework)
- MongoEngine (MongoDB ORM)
- Pydantic (data validation)

### Databases
- MongoDB (document store for products, categories, questions)

### Messaging/Queue Systems
- Not implemented in current codebase (Celery, Redis, RabbitMQ: not present)

### Cloud Services Used
- OpenAI API (for AI responses)
- Google Gemini API (fallback for AI responses)

### Infrastructure-as-Code
- Dockerfile for containerization

### DevOps Tools
- Docker
- Uvicorn (ASGI server)

---

## 3. System Architecture

### Cloud Architecture Diagram Description
- **API Layer**: FastAPI app, exposed via Uvicorn, containerized with Docker.
- **Database Layer**: MongoDB, accessed via MongoEngine.
- **AI Layer**: External calls to OpenAI and Gemini APIs.

### Deployment Architecture
- Single container deployment (Docker)
- Exposes port 8000
- Environment variables for DB and API keys

### Networking Overview
- API accessible over HTTP (default: port 8000)
- CORS enabled for all origins

### Load Balancers, Autoscaling, Gateways
- Not present in current codebase; can be added via cloud provider (e.g., AWS ALB, GCP Load Balancer)

### Service-to-Service Interactions
- Internal: FastAPI routers interact with MongoDB and external AI APIs
- External: OpenAI, Gemini API calls

### Data Flow Description
1. User sends request to API endpoint.
2. API authenticates via API key, checks rate limit.
3. Product/category/question data fetched from MongoDB.
4. If no answer found, AI service generates response.
5. Response returned to user.

---

## 4. Entity & Data Model Documentation

### List of All Entities
- Product
- Product Category
- Brand
- Vendor
- Manufacture Unit
- ShopifyProduct
- Product Questions

### Entity-Relationship Descriptions
- Product references Brand, Vendor, Category, Manufacture Unit.
- Category supports hierarchy (parent/child).
- ShopifyProduct references Category.
- Product Questions reference Category.

### Schemas, Attributes, Constraints
- See `models/schemas.py` for full schema definitions.
- Pydantic models for API requests/responses.
- MongoEngine models for DB entities.

### ORM Modeling Notes
- MongoEngine used for all DB models.
- ReferenceField for relationships.
- ListField, DictField for flexible attributes.

---

## 5. Celery Worker Architecture

*Not implemented in current codebase.*
- No Celery tasks, scheduling, or monitoring present.

---

## 6. API Documentation

### Full Endpoint List
- `POST /api/v1/chat` — Chat with AI about a product
- `GET /api/v1/questions` — Get product-related questions
- `GET /api/v1/config` — Get widget configuration
- `GET /api/v1/fourth_level_categories` — List categories
- `GET /api/v1/products` — Filter/search products

### HTTP Methods
- GET, POST

### Request/Response Examples
- See Pydantic models in `models/schemas.py` for request/response formats.

### Authentication/Authorization
- API key required in header (`X-API-KEY`)
- Rate limiting enforced per key

### Error Codes
- 400: Bad request
- 401: Unauthorized (invalid API key)
- 429: Rate limit exceeded
- 500: Internal server error

### Pagination/Filtering Rules
- Product filtering via query params (category, brand, attributes)
- No explicit pagination implemented

### Webhooks
- Not present

---

## 7. Environment Setup

### Local Development Environment
- Python 3.11
- MongoDB instance
- Docker (optional)

### Environment Variables List & Purpose
- `MONGODB_HOST`: MongoDB connection string
- `MONGODB_NAME`: Database name
- `OPEN_AI_KEY`: OpenAI API key
- `GOOGLE_GEMINI_API_KEY`: Gemini API key

### Configurations for Dev/Staging/Production
- Use `.env` file for environment variables
- Dockerfile supports environment variable injection

### Docker Setup
- Build: `docker build -t chatbot-backend .`
- Run: `docker run -p 8000:8000 --env-file .env chatbot-backend`

---

## 8. Database Backups & Disaster Recovery

*Not implemented in current codebase.*
- No backup/restore scripts or policies present
- Recommend using MongoDB tools (mongodump/mongorestore) externally

---

## 9. Deployment & CI/CD

### Pipeline Steps
- Not present in codebase; recommend GitHub Actions or similar

### Automatic Tests
- No test suite present

### Build → Release → Deploy Lifecycle
- Build Docker image
- Deploy container

### Versioning
- Manual; recommend semantic versioning

---

## 10. Security Considerations

### API Security
- API key authentication
- Rate limiting

### Secrets Management
- Environment variables
- No vault integration

### Access Control
- Per-API-key rate limits

### Data Encryption
- Not implemented; recommend TLS for API traffic

### Compliance Notes
- No explicit GDPR/SOC2 features; recommend review for production

---

## 11. Maintenance & Observability

### Logging
- Print statements for errors and info
- Recommend structured logging for production

### Metrics
- Not implemented; recommend Prometheus/Grafana

### Alerting
- Not implemented

### Monitoring Stack
- Not present; recommend integration with cloud monitoring tools

---

## 12. Appendices

### Glossary
- **API Key**: Token for authenticating API requests
- **MongoEngine**: Python ORM for MongoDB
- **Pydantic**: Data validation library
- **OpenAI/Gemini**: AI services for generating responses

### Troubleshooting
- **MongoDB connection failed**: Check `MONGODB_HOST` and `MONGODB_NAME` in `.env`
- **Invalid API Key**: Ensure correct key in request header
- **Rate limit exceeded**: Reduce request frequency
- **AI response errors**: Check API keys and service status

### Common Errors and Fixes
- 401 Unauthorized: Invalid/missing API key
- 429 Rate Limit: Too many requests; wait and retry
- 500 Internal Error: Check logs for stack trace

---

python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
