import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import ToolMessage
from langchain_core.messages import HumanMessage
from langchain_core.messages import AIMessage

import socket

load_dotenv() #pulls keys from .env into os.getenv

chat_history = [HumanMessage(content="What are the open ports on the target IP?")]

api_key = os.getenv("DEEPSEEK_API_KEY")

#Creates 'Agent' Object with access to DeepSeek API and model, then binds tools to it for use in the loop below
agent = ChatDeepSeek(model ="deepseek-coder", api_key=api_key)

task_completed = False
loop_reps = 0
chat_history = []

@tool
def run_port_scan(target_ip: str):
    """Runs a scan on the open connections or ports on target IP to find potential vulnerabilities"""
    #code to trigger scanner
    open_ports = []
    ports_to_check = [80, 443, 22, 21]
    for port in ports_to_check:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)  # Set a timeout for the connection attempt
        result = sock.connect_ex((target_ip, port))
        if result == 0:
            open_ports.str(port)
        sock.close()
    formatted_ports = ", ".join(open_ports)
    return f"Open ports found at {target_ip}: {formatted_ports}"

@tool
def create_task(objective: str):
    """Decide on what to do with list of potential vulnerabilities from IP"""

@tool
def execute_tool(command: str):
    """Execute necessary tool for based off decisions to fulfil task"""

    # Gather tools into a list
tools = [create_task, run_port_scan, execute_tool]

# Restrict agent to only use these tools
agent_with_tools = agent.bind_tools(tools)

if api_key == None:
    print("API Key is missing")
    exit()

tool_map = {
    "run_port_scan": run_port_scan,
    "create_task": create_task,
    "execute_tool": execute_tool}

while not task_completed and loop_reps < 10:
    if loop_reps == 0:
    #Ask AI what to do based off history
        new_message = AIMessage(
        content = "",
        tool_calls=[{
            "name": "run_port_scan",
            "args": {"target_ip": "192.168.1.1"},
            "id": "call_mock_123"
        }]
        )   
    else:
        new_message = AIMessage(content="Scan finished. Port 80 is open. What do you want to do next?")
    #Add thought to our history
    chat_history.append(new_message)
    #Action Step if AI wants to use a tool, we execute it and add the result to our history

    if new_message.tool_calls:
        print(f"Loop {loop_reps}: AI wants to use a tool, executing...")
        tool_call = new_message.tool_calls[0]
        #Extract the tool name and arguments from the tool call
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        # Look up the function in our map
        function_to_run = tool_map[tool_name]

        #run the function with the provided arguments
        tool_result = function_to_run.invoke(tool_args)

        #Create message that contains tool output
        observation = ToolMessage(
        content = str(tool_result),
        tool_call_id = tool_call["id"] #tells AI which request this answers
        )  

        #Add to history
        chat_history.append(observation) 

    else:
        print(f"Loop {loop_reps}: AI says: {new_message.content}")
        task_completed = True
    loop_reps += 1

