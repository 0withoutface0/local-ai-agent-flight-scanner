# RAG on Flight Data

![flight search AI](https://github.com/user-attachments/assets/513d8116-5b4a-49f0-9aaa-47bc8d5622f3)


## Frontend Repo

[https://github.com/harsh-vardhhan/ai-agent-flight-scanner-frontend](https://github.com/harsh-vardhhan/ai-agent-flight-scanner-frontend)

## Technical spec

| Spec                                     |           |
|----------------------------------------- |-----------|
| Platform to run LLMs                     | LM Studio (local) |
| LLM for SQL                              | qwen/qwen3-30b-a3b-2507 (example) |
| LLM for Vector Database                  | lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF (example) |
| AI agent framework                       | LangChain |
| SQL Database                             | SQLite    |
| Vector Database                          | Chroma    |
| REST framework                           | FastAPI   |

## Application architecture

<img width="640" alt="application_architecture" src="https://github.com/user-attachments/assets/07ec6397-ac72-4be1-a19f-ba6809ce57da" />


## Create `.env` file and set environment variables

```bash
# Default provider is LM Studio (local)
DEFAULT_LLM_PLATFORM=LMSTUDIO_OPENAI

# LM Studio OpenAI-compatible endpoint
LMSTUDIO_OPENAI_BASE_URL=http://127.0.0.1:1234/v1
LMSTUDIO_API_KEY=lm-studio

# Use model IDs that you loaded in LM Studio
FLIGHT_LLM_MODEL=qwen/qwen3-30b-a3b-2507
LUGGAGE_LLM_MODEL=lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF
```

If you want to override provider per task, set `FLIGHT_LLM_PLATFORM` and `LUGGAGE_LLM_PLATFORM` to one of:
- `LMSTUDIO_OPENAI` (fully local via LM Studio)
- `OLLAMA`
- `GROQ`

Model recommendation for parity with the original setup:
- `FLIGHT_LLM_MODEL=qwen/qwen3-30b-a3b-2507` (closest to original qwen3-32b intent)
- `LUGGAGE_LLM_MODEL=lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF` (good small local instruct model)


## Live flight sync (Amadeus free tier)

The app can now refresh `flights.db` from the Amadeus Flight Offers API on a schedule, while keeping the same SQL + LLM query flow.

Add these variables to `.env`:

```bash
# Enable periodic online refresh
ENABLE_ONLINE_FLIGHT_SYNC=true
FLIGHT_SYNC_INTERVAL_MINUTES=360
FLIGHT_SYNC_DAYS_AHEAD=21
FLIGHT_SYNC_MAX_PER_DAY=8

# Optional route list (JSON array)
# FLIGHT_SYNC_ROUTES=[{"origin":"New Delhi","destination":"Hanoi"},{"origin":"Mumbai","destination":"Ho Chi Minh City"}]

# Amadeus self-service test credentials
AMADEUS_CLIENT_ID=your_amadeus_client_id
AMADEUS_CLIENT_SECRET=your_amadeus_client_secret
```

Notes:
- Register at Amadeus for Developers and use the Self-Service test environment keys.
- The startup flow still seeds from `data/flight_data.json` if the DB is empty, then online sync updates/inserts records.
- Current city-to-IATA mapping is in `app/providers/amadeus.py`. Add more cities there as needed.

## Running application

```
python3 app/main.py
```

## Prompt testing

### Basic Price Queries (India to Vietnam)

| Prompt                                                                                       |
|---------------------------------------------------------------------------------------------|
| What is the cheapest flight from New Delhi to Hanoi?                                        |
| Find the lowest price flight from Mumbai to Ho Chi Minh City                                |
| Show me the cheapest flight from New Delhi to Da Nang                                       |
| What is the lowest fare from Mumbai to Phu Quoc?                                            |

### Basic Price Queries (Vietnam to India)

| Prompt                                                                                       |
|---------------------------------------------------------------------------------------------|
| What is the cheapest flight from Hanoi to New Delhi?                                        |
| Find the lowest price flight from Ho Chi Minh City to Mumbai                                |
| Show me the cheapest flight from Da Nang to New Delhi                                       |
| What is the lowest fare from Phu Quoc to Mumbai?                                            |

### Price Range Queries (Generic)

| Prompt                                                                                       |
|---------------------------------------------------------------------------------------------|
| Show me flights from New Delhi to Hanoi ordered by price                                    |
| List all flights from Ho Chi Minh City to Mumbai from lowest to highest price              |
| What are the available flights from Mumbai to Da Nang sorted by fare?                      |
| Find flights from Phu Quoc to New Delhi ordered by cost                                    |

### Flight Type Specific

| Prompt                                                                                       |
|---------------------------------------------------------------------------------------------|
| Show me all direct flights from New Delhi to Ho Chi Minh City                              |
| List connecting flights from Hanoi to Mumbai                                               |
| What types of flights are available from New Delhi to Da Nang?                             |
| Find direct flights from Phu Quoc to Mumbai                                               |

### Comparative Queries

| Prompt                                                                                       |
|---------------------------------------------------------------------------------------------|
| Compare prices of flights from New Delhi to all Vietnamese cities                          |
| Show me the cheapest routes from Mumbai to Vietnam                                         |
| List all flight options from Hanoi to Indian cities                                        |
| Compare fares from Ho Chi Minh City to Indian destinations                                 |

### Round Trip Queries

| Prompt                                                                                       |
|---------------------------------------------------------------------------------------------|
| Find the cheapest round trip from New Delhi to Hanoi                                       |
| Show me round trip options between Mumbai and Ho Chi Minh City                             |
| What are the most affordable round trip flights from New Delhi to Da Nang?                |
| List round trip flights between Mumbai and Phu Quoc                                        |
| List cheapest round trip flights between Mumbai and Phu Quoc                               |
| Find the cheapest return flight between New Delhi and Hanoi with at least 7 days gap       |
| Show exactly one cheapest flight from New Delhi to Hanoi and exactly one from Hanoi to New Delhi, which should be at least 7 days later |

### Statistical Analysis

| Prompt                                                                                       |
|---------------------------------------------------------------------------------------------|
| What's the average price of flights from New Delhi to Vietnamese cities?                   |
| Compare fares between all India-Vietnam routes                                             |
| Show me the price distribution of flights from Vietnamese cities to Mumbai                 |
| Which Vietnam-India route has the most varying fares?                                      |

### Combination Queries

| Prompt                                                                                       |
|---------------------------------------------------------------------------------------------|
| Find the cheapest direct flight from New Delhi to any Vietnamese city                      |
| List the most affordable flights from Vietnamese cities to Mumbai                          |
| Show me the top 5 best-value routes between India and Vietnam                              |
| What are the most economical flights from Hanoi to Indian cities?                          |
