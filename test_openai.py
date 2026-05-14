import json
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function
msg = ChatCompletionMessage(role="assistant", content=None, tool_calls=[ChatCompletionMessageToolCall(id="call_123", type="function", function=Function(name="test", arguments="{}"))])
print(json.dumps(msg.model_dump()))
