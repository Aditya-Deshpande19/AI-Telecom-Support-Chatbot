import os

# --- HARDCODE CONFIGURATION (For Debugging Only) ---
# Paste your key inside the quotes below. Do not use the .env file for this test.
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "lsv2_pt_..." # <--- REPLACE THIS WITH YOUR KEY
os.environ["LANGCHAIN_PROJECT"] = "Debug_Test_Project"

print(f"Testing Connection with Key: {os.environ['LANGCHAIN_API_KEY'][:10]}...")

try:
    # 1. Test Direct Authentication
    from langsmith import Client
    client = Client()
    
    # Try to list projects. If this fails, your Key is wrong or internet is blocked.
    projects = list(client.list_projects())
    project_names = [p.name for p in projects]
    
    print("\n✅ AUTHENTICATION SUCCESSFUL!")
    print(f"   Found {len(projects)} projects: {project_names}")
    
    # 2. Test Sending a Trace
    print("\nAttempting to send a test trace...")
    from langchain_ollama import ChatOllama
    
    llm = ChatOllama(model="llama3.1")
    response = llm.invoke("Say 'Connection verified'")
    
    print(f"   LLM Response: {response.content}")
    print("   -> NOW CHECK YOUR DASHBOARD. Look for 'Debug_Test_Project'.")

except ImportError:
    print("\n❌ Error: 'langsmith' library not installed. Run 'pip install langsmith'")
except Exception as e:
    print(f"\n❌ CONNECTION FAILED: {e}")
    print("   Tip: Check if you are behind a corporate firewall or VPN.")