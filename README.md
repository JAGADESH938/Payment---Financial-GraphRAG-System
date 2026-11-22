# PaymentGraph - Financial GraphRAG System

A real-time GraphRAG (Graph Retrieval-Augmented Generation) application that leverages Neo4j and Groq LLMs (`llama-3.1-8b-instant`) to store and query payment transaction logs.

---

## 📁 Project Structure

```plaintext
PaymentGraph - II/
├── .env                 # Neo4j and Groq environment variables
├── .gitignore           # Git ignore configurations
├── LICENSE              # MIT License
├── README.md            # Project documentation
├── requirements.txt     # Python package requirements
├── run_cli.bat          # 1-click launcher for the interactive CLI application
├── run_ui.bat           # 1-click launcher for the Streamlit Web UI application
│
├── data/                # Data storage
│   ├── transaction_logs_450_logs_final_correct.json  # Primary dataset for CLI
│   └── paymets.json                                  # Sample dataset for Web UI
│
├── src/                 # Source code
│   ├── cli.py           # Terminal interactive GraphRAG application
│   └── app.py           # Streamlit Web UI application
│
└── .venv/               # Isolated Python virtual environment
```

---

## ⚙️ Prerequisites & Setup

1. **Python**: Python 3.10+ (Current `.venv` uses Python 3.13)
2. **Neo4j**: Neo4j Desktop or local Neo4j instance running on port `7687`
3. **Groq API Key**: A valid API key from [console.groq.com](https://console.groq.com/)

### Environment Configuration (`.env`)

Ensure the `.env` file in the project root contains:

```env
GROQ_API_KEY=your_groq_api_key_here
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
NEO4J_DATABASE=neo4j
```

---

## 🚀 How to Run

### 1. Interactive CLI Tool

Double-click `run_cli.bat` or run:

```powershell
.\.venv\Scripts\python.exe src\cli.py
```

- When prompted for the JSON path, press **Enter** to load `data/transaction_logs_450_logs_final_correct.json`.
- Enter the Transaction ID (e.g., `TXN10001`) and select from the available Flows, Services, and Interfaces shown on screen.
- Ask questions in plain English (e.g., *"What is the transaction amount and status?"*).

### 2. Streamlit Web UI

Double-click `run_ui.bat` or run:

```powershell
.\.venv\Scripts\streamlit.exe run src\app.py
```

- Click **Connect** in the sidebar (credentials automatically load from `.env`).
- Upload `data/paymets.json` and click **Process Data**.
- Query the graph database and view generated Cypher queries with natural language summaries.
