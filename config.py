CUSTOM_CORRECTIONS = {
    # Mobile
    "mobel": "mobile",
    "moble": "mobile",
    "moblie": "mobile",
    "mobiie": "mobile",
    "mobil": "mobile",

    # Jio brand
    "jio": "Jio",
    "jiofiber": "Jio Fiber",
    "jiofibr": "Jio Fiber",
    "jiofibre": "Jio Fiber",
    "jiofibe": "Jio Fiber",
    "jio4g": "Jio 4G",
    "jio5g": "Jio 5G",

    # Network
    "ntwork": "network",
    "ntwrk": "network",
    "netwrk": "network",
    "netwerk": "network",
    "netowrk": "network",

    # Recharge
    "recharg": "recharge",
    "rechareg": "recharge",
    "rechrge": "recharge",
    "rcharge": "recharge",
    "recharje": "recharge",

    # Internet
    "interneet": "internet",
    "intrnet": "internet",
    "internt": "internet",
    "inernet": "internet",

    # Connection
    "conection": "connection",
    "connction": "connection",
    "connetion": "connection",
    "connecton": "connection",

    # Balance
    "balence": "balance",
    "ballance": "balance",
    "balace": "balance",

    # Validity
    "validty": "validity",
    "validy": "validity",
    "validiy": "validity",

    # SIM
    "simcard": "sim card",
    "sim-card": "sim card",

    # Signal
    "singal": "signal",
    "signel": "signal",
    "sinal": "signal",

    # Payment
    "paymet": "payment",
    "paymnt": "payment",
    "paiment": "payment",

    # Phone
    "fone": "phone",
    "fon": "phone",

    # Not
    "nt": "not",

    # Activate
    "activte": "activate",
    "actvate": "activate",
    "actiate": "activate",

    # Calling
    "callng": "calling",
    "caling": "calling",

    # Working
    "wrking": "working",
    "workng": "working",
    "wrk": "working",
}

DB_PATH = "./chroma_db_v4"
COLLECTION_NAME = "jio_knowledge_base"
EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "llama3:8b"

HARMFUL_KEYWORDS = [
    # Security threats
    "hack", "hacking", "hacked", "malware", "virus", "exploit",
    "ddos", "phishing", "ransomware", "spyware", "keylogger",
    "botnet", "trojan", "rootkit", "sql injection", "brute force",

    # Illegal activity
    "steal", "stolen", "bypass", "crack", "cracking", "piracy",
    "illegal", "clone sim", "sim swap", "intercept", "sniff",
    "eavesdrop", "wiretap", "spoof",

    # Personal data abuse
    "track someone", "spy on", "monitor someone", "stalk",
    "location track", "call records of", "someone's data",

    # Fraud
    "fraud", "scam", "fake recharge", "cheat", "manipulate bill",
]

JIO_KEYWORDS = [
    "jio", "fiber", "plan", "recharge", "network", "internet",
    "speed", "connectivity", "gateway", "sim", "data", "tariff",
    "broadband", "prepaid", "postpaid", "4g", "5g", "volte",
    "hotspot", "router", "signal", "billing", "activation"
]

KEYWORD_THRESHOLD = 3
MAX_REWRITES = 2
RETRIEVER_K = 3

MAX_HISTORY_TURNS = 5        # retain only last 5 turns (10 messages) of conversation
MAX_REQUEST_SIZE_BYTES = 2 * 1024 * 1024  # 2MB request size limit

MAX_CONTEXT_CHARS = 1500        # max chars of retrieved context passed to LLM per answer
MAX_PROMPT_CONTEXT_CHARS = 800  # max chars of context passed to hallucination check