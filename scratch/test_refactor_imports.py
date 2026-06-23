from langchain_classic.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
import os
import dotenv

dotenv.load_dotenv()

@tool
def dummy_tool(x: int) -> str:
    """A dummy tool that returns string representation of x."""
    return f"The tool output is: {x}"

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("GMS_API_KEY"),
    base_url="https://gms.ssafy.io/gmsapi/api.openai.com/v1"
)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. Always reply in Korean."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_openai_tools_agent(llm, [dummy_tool], prompt)
executor = AgentExecutor(agent=agent, tools=[dummy_tool], verbose=True)

res = executor.invoke({
    "input": "dummy_tool을 사용해서 42를 처리해줘",
    "chat_history": []
})
print("Result:", res)
