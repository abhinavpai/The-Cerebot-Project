import gradio as gr
from Functions import chat_router

def cerebot_ui(user_input, history, state):
    response, new_state = chat_router(user_input, state)
    history = history + [(user_input, response)]
    return history, new_state

with gr.Blocks(title="Cerebot") as demo:
    gr.Markdown(
        "## 🧠 Cerebot: Mental Health Screening Assistant\n"
        "Describe your symptoms, review DSM-5 checklists, and chat with the AI.\n"
        "⚠️ **Note:** This is NOT a medical diagnosis. Always consult a licensed professional."
    )

    chatbot = gr.Chatbot(height=400, label="Cerebot")
    msg = gr.Textbox(label="Your input", placeholder="Type here and press Enter…")
    state = gr.State({"stage": "awaiting_description"})  # store conversation state
    clear = gr.Button("Restart")

    msg.submit(cerebot_ui, [msg, chatbot, state], [chatbot, state])
    clear.click(lambda: ([], {"stage": "awaiting_description"}), None, [chatbot, state])

demo.launch()
