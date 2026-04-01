import os
import ipaddress
from dotenv import load_dotenv
from langchain_core.tools import tool
# from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import ToolMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

import socket

load_dotenv() #pulls keys from .env into os.getenv

api_key = os.getenv("GOOGLE_API_KEY")

task_completed = False
loop_reps = 0


operator_protocol = """You are an autonomous security agent. 
When given a primary objective by the user, you must strictly follow this workflow:

1. DISCOVERY: Use the `discover_hosts` tool if the user provides a range (CIDR) to find active hosts. This will add new tasks to your queue for each discovered host.
2. PLANNING: Do not take immediate action. Use the `create_task` tool to break the user's objective into smaller, pending tasks.
3. FETCHING: Use the `get_next_task` tool to pull the current 'in_progress' task from the queue.
4. EXECUTING: Use your specific action tools (like `run_port_scan`) to complete the fetched task.
5. COMPLETING: Once you have the observation from the action tool, use the `complete_task` tool to mark the task as done.
6. LOOPING: Return to step 2 until the `get_next_task` tool reports no pending tasks remaining.
"""
user_prompt = """What are the open ports on the target IP 192.168.1.1/29?"""

#Prompt to the AI
chat_history = [SystemMessage(content=operator_protocol), HumanMessage(content=user_prompt)]

@tool
def run_port_scan(target_ip: str):
    """Runs a scan on the open connections or ports on target IP to find potential vulnerabilities"""
    print(f"[*] Commencing port scan on {target_ip}...")
    #code to trigger scanner
    open_ports = []
    ports_to_check = [80, 443, 22, 21]
    for port in ports_to_check:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)  # Set a timeout for the connection attempt
        result = sock.connect_ex((target_ip, port))
        if result == 0:
            open_ports.append(str(port))
        sock.close()
    if not open_ports:
        return f" Scan complete. No open ports found at {target_ip}."
    
    formatted_ports = ", ".join(open_ports)
    return f"Open ports found at {target_ip}: {formatted_ports}"

# We need a place to store tasks safely outside the AI's temporary chat memory
task_queue = []

@tool
# Blank 2: What Python data type should we enforce for these arguments?
def create_task(task_name: str, target_ip: str):
    
    # Blank 3: What must we write here so the AI 'Brain' understands this tool?
    """Use this tool to add a new multi-step goal or action item to your pending queue. Always use this to plan your next moves before executing them."""
    
    new_task = {
        "task_name": task_name,
        "target_ip": target_ip,
        "status": "pending"
    }
    
    #adds our dictionary to the queue list?
    task_queue.append(new_task)
    
    return f"Success: Task '{task_name}' added to queue."

@tool
def get_next_task():
    """Fetches the next pending task from the task queue to execute."""
    
    for task in task_queue:
        if task["status"] == "pending":
            task["status"] = "in_progress"
            return f"Next task: {task['task_name']} on target {task['target_ip']}"
            
    return "[*] No pending tasks remaining."

@tool
def complete_task(task_name: str):
    """Checks off completed tasks from the task queue."""
    for task in task_queue:
        if task["task_name"] == task_name:
            task["status"] = "completed"
            return f"{task['task_name']} on target {task['target_ip']} completed."
    return f"[*] Task '{task_name}' not found in queue."

@tool
def execute_tool(command: str):
    """Execute necessary tool for based off decisions to fulfil task"""

#create IPv4Network object to validate IP addresses. /24 means we are looking at a subnet mask of 255.255.255.0, which allows for 256 total addresses. /32 means we are looking at a single IP address.
@tool
def discover_hosts(cidr_range: str):
    """Expands a CIDR range to find active hosts in range and adds them to the task queue for scanning."""
    try:
        network = ipaddress.IPv4Network(cidr_range)
        hosts_added = 0
        for ip in network.hosts():
            # Here we could add a quick ping check to see if the host is active before adding to the queue
            #change ip address into string
            ip_str = str(ip)
            create_task(task_name=f"Port scan on {ip_str}", target_ip=ip_str)
            hosts_added += 1
        return f"Discovery complete. {hosts_added} hosts added to task queue for scanning."
    except Exception as e:
        return f"Error: Invalid CIDR range provided. Please provide a valid range like '192.168.1.0/24'"

    # Gather tools into a list
tools = [create_task, get_next_task, run_port_scan, complete_task, execute_tool, discover_hosts]

agent = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)

# Restrict agent to only use these tools
agent_with_tools = agent.bind_tools(tools)

if api_key == None:
    print("API Key is missing")
    exit()

tool_map = {
    "run_port_scan": run_port_scan,
    "create_task": create_task,
    "get_next_task": get_next_task,
    "complete_task": complete_task,
    "execute_tool": execute_tool,
    "discover_hosts": discover_hosts}

print(f"[*] Checking envelope: {chat_history}")

while not task_completed and loop_reps < 10:
        # if loop_reps == 0:
    # #Ask AI what to do based off history
    #     new_message = AIMessage(
    #     content = "",
    #     tool_calls=[{
    #         "name": "run_port_scan",
    #         "args": {"target_ip": "192.168.1.1"},
    #         "id": "call_mock_123"
    #     }]
    #     )   
    # else:
    #     new_message = AIMessage(content="Scan finished. Port 80 is open. What do you want to do next?")
    print(f"[*] AI is thinking...")
    new_message = agent_with_tools.invoke(chat_history)
    #Add thought to our history
    chat_history.append(new_message)
    #Action Step if AI wants to use a tool, we execute it and add the result to our history

    if new_message.tool_calls:
        print(f"Loop {loop_reps}: AI wants to use a tool, executing...")
        tool_call = new_message.tool_calls[0]
        #Extract the tool name and arguments from the tool call
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        # Look up the function in our map, use .get to catch any errors if the AI tries to call a tool we don't have
        function_to_run = tool_map.get(tool_name)

        #run the function with the provided arguments
        tool_result = function_to_run.invoke(tool_args)
        print(f"[*] Tool Output: {tool_result}")

        #Create message that contains tool output
        observation = ToolMessage(
        content = str(tool_result),
        tool_call_id = tool_call["id"] #tells AI which request this answers
        )  

        #Add to history
        chat_history.append(observation) 

    else:
        # Check if content is a list (standard for newer Gemini models)
        if isinstance(new_message.content, list):
            # Extract text from the first content block
            final_text = new_message.content[0].get('text', '')
        else:
            # Fallback if it's already a string
            final_text = new_message.content
            
        print(f"Loop {loop_reps}: AI says: {final_text}")
        task_completed = True
    loop_reps += 1

