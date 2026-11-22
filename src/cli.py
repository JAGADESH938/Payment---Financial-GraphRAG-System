import json
import os
import re
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph
from groq import Groq

# -----------------------------
# LOAD ENV
# -----------------------------

# Load .env from current directory or project root
load_dotenv()
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_path = os.path.join(_project_root, ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# -----------------------------
# CONNECT GRAPH
# -----------------------------

graph = None
try:
    if NEO4J_URI and NEO4J_USERNAME and NEO4J_PASSWORD:
        graph = Neo4jGraph(
            url=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD
        )
except Exception as e:
    print(f"[INFO] Neo4j is not connected yet ({e}). It will connect when the database starts.")

client = None
try:
    if GROQ_API_KEY:
        client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    print(f"[INFO] Groq client not initialized: {e}")

# -----------------------------
# TEXT NORMALIZATION
# -----------------------------

def clean_text(text):
    return re.sub(r"[\s_]", "", text.lower())


def smart_match(user_input, valid_list):

    user_clean = clean_text(user_input)

    for item in valid_list:
        if user_clean == clean_text(item):
            return item

    for item in valid_list:
        if user_clean in clean_text(item):
            return item

    return None


def get_valid_values(label):

    query = f"""
    MATCH (n:{label})
    RETURN DISTINCT n.name AS name
    """

    result = graph.query(query)

    return [r["name"] for r in result]

# -----------------------------
# CLEAR DATABASE
# -----------------------------

def clear_database():

    graph.query("MATCH (n) DETACH DELETE n")

# -----------------------------
# FINAL FIXED JSON LOADER
# -----------------------------

def load_json(file_path):

    clear_database()

    with open(file_path, "r") as f:
        data = json.load(f)

    count = 0

    for record in data:

        query = """
        MERGE (t:Transaction {id:$tx})

        MERGE (f:Flow {
            name:$flow,
            tx:$tx
        })

        MERGE (t)-[:HAS_FLOW]->(f)

        MERGE (s:Service {
            name:$service,
            flow:$flow,
            tx:$tx
        })

        MERGE (f)-[:HAS_SERVICE]->(s)

        MERGE (i:Interface {
            name:$interface,
            service:$service,
            flow:$flow,
            tx:$tx
        })

        MERGE (s)-[:HAS_INTERFACE]->(i)

        CREATE (log:Log {
            timestamp:$timestamp
        })

        MERGE (i)-[:HAS_LOG]->(log)

        CREATE (p:Payment {
            amount:$amount,
            currency:$currency,
            status:$status
        })

        MERGE (log)-[:HAS_PAYMENT]->(p)

        CREATE (d:Details {
            channel:$channel,
            priority:$priority
        })

        MERGE (log)-[:HAS_DETAILS]->(d)

        CREATE (sender:Account {
            iban:$sender
        })

        CREATE (receiver:Account {
            iban:$receiver
        })

        MERGE (log)-[:SENT_BY]->(sender)
        MERGE (log)-[:RECEIVED_BY]->(receiver)
        """

        graph.query(query, {

            "tx": record["transaction_id"],
            "flow": record["payment_flow"],
            "service": record["service"],
            "interface": record["interface"],

            "timestamp": record["timestamp"],

            "amount": record["payment"]["amount"],
            "currency": record["payment"]["currency"],
            "status": record["payment"]["status"],

            "sender": record["accounts"]["sender"]["IBAN"],
            "receiver": record["accounts"]["receiver"]["IBAN"],

            "channel": record["format"]["details"]["channel"],
            "priority": record["format"]["details"]["priority"]

        })

        count += 1

    print(f"\nLoaded {count} logs into Neo4j")

# -----------------------------
# FINAL STRICT QUERY
# -----------------------------

def run_cypher(context):

    query = """
    MATCH (t:Transaction {id:$tx_id})
          -[:HAS_FLOW]->(f:Flow {
                name:$flow,
                tx:$tx_id
          })
          -[:HAS_SERVICE]->(s:Service {
                name:$service,
                flow:$flow,
                tx:$tx_id
          })
          -[:HAS_INTERFACE]->(i:Interface {
                name:$interface,
                service:$service,
                flow:$flow,
                tx:$tx_id
          })
          -[:HAS_LOG]->(log)

    MATCH (log)-[:HAS_PAYMENT]->(p)
    MATCH (log)-[:HAS_DETAILS]->(d)

    OPTIONAL MATCH (log)-[:SENT_BY]->(sender)
    OPTIONAL MATCH (log)-[:RECEIVED_BY]->(receiver)

    RETURN {
        amount:p.amount,
        currency:p.currency,
        status:p.status,
        sender:sender.iban,
        receiver:receiver.iban,
        channel:d.channel,
        priority:d.priority,
        timestamp:log.timestamp
    } AS result

    ORDER BY datetime(log.timestamp) DESC
    LIMIT 1
    """

    result = graph.query(query, context)

    print("\nDEBUG RESULT:", result)

    return result

# -----------------------------
# GROQ ANSWER
# -----------------------------

def llm_answer(result, question):

    if not client:
        return f"[Groq LLM Offline / Invalid API Key]\nRaw database result:\n{json.dumps(result, indent=2, default=str)}"

    prompt = f"""
User Question:
{question}

Database Result:
{result[:1]}

Answer clearly using only database values.
"""

    try:
        res = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"[Groq API Error: {e}]\nRaw database result:\n{json.dumps(result, indent=2, default=str)}"

# -----------------------------
# GET CONTEXT
# -----------------------------

def get_context():

    valid_flows = get_valid_values("Flow")
    valid_services = get_valid_values("Service")
    valid_interfaces = get_valid_values("Interface")

    print("\n--- Available Database Values ---")
    if valid_flows:
        print(f"Flows:      {', '.join(valid_flows)}")
    if valid_services:
        print(f"Services:   {', '.join(valid_services)}")
    if valid_interfaces:
        print(f"Interfaces: {', '.join(valid_interfaces)}")

    tx_id = input("\nEnter Transaction ID (e.g. TXN10001): ").strip()
    flow_input = input("Enter Payment Flow: ").strip()
    service_input = input("Enter Service: ").strip()
    interface_input = input("Enter Interface: ").strip()

    flow = smart_match(flow_input, valid_flows)
    service = smart_match(service_input, valid_services)
    interface = smart_match(interface_input, valid_interfaces)

    return {

        "tx_id": tx_id,
        "flow": flow,
        "service": service,
        "interface": interface
    }

# -----------------------------
# MAIN LOOP
# -----------------------------

def main():

    global graph, client

    if graph is None:
        try:
            print("\nConnecting to Neo4j database...")
            graph = Neo4jGraph(
                url=NEO4J_URI,
                username=NEO4J_USERNAME,
                password=NEO4J_PASSWORD
            )
            print("Connected to Neo4j successfully!")
        except Exception as e:
            print(f"\n[ERROR] Could not connect to Neo4j at '{NEO4J_URI}'.")
            print("Please ensure your Neo4j instance is running and credentials in .env are correct.")
            print(f"Details: {e}")
            return

    if client is None and GROQ_API_KEY:
        try:
            client = Groq(api_key=GROQ_API_KEY)
        except Exception as e:
            print(f"[WARNING] Groq client initialization failed: {e}")

    print("\n--- Loading JSON into Graph ---")

    data_dir = os.path.join(_project_root, "data")
    default_file = os.path.join(data_dir, "transaction_logs_450_logs_final_correct.json")
    prompt_file = f"\nEnter JSON file path [Press Enter for default: data/transaction_logs_450_logs_final_correct.json]: "
    file_path = input(prompt_file).strip().replace('"', '')

    if not file_path:
        file_path = default_file
    elif not os.path.isabs(file_path):
        for candidate in [
            os.path.join(data_dir, file_path),
            os.path.join(os.getcwd(), file_path),
            os.path.join(_project_root, file_path)
        ]:
            if os.path.exists(candidate):
                file_path = candidate
                break

    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        return

    print(f"Loading data from: {file_path}")
    load_json(file_path)

    context = get_context()

    while True:

        question = input("\nAsk your question: ")

        result = run_cypher(context)

        answer = llm_answer(result, question)

        print("\nFinal Answer:")
        print(answer)

        print("\nOptions:")
        print("1 Follow-up")
        print("2 Change transaction")
        print("3 Exit")

        choice = input("Enter choice: ")

        if choice == "1":
            continue

        elif choice == "2":
            context = get_context()

        else:
            break


if __name__ == "__main__":

    main()
