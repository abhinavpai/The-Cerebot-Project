import gradio as gr
from FunctionsCorrected import gradio_step, gradio_init_state, gradio_welcome_text, gradio_reset

def on_submit(user_input, messages, state):
    reply, new_state = gradio_step(user_input, state)
    messages = (messages or []) + [
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": reply},
    ]
    return messages, new_state, ""  # clear textbox

with gr.Blocks(title="Cerebot") as demo:
    gr.Markdown("## Cerebot")
    chatbot = gr.Chatbot(label="Cerebot", height=500, type="messages")
    msg = gr.Textbox(placeholder="Type here and press Enter…")
    state = gr.State(gradio_init_state())
    clear = gr.Button("Restart")
    chatbot.value = [{"role": "assistant", "content": gradio_welcome_text()}]
    msg.submit(on_submit, inputs=[msg, chatbot, state], outputs=[chatbot, state, msg])
    def on_clear():
        s, cleared = gradio_reset()
        return [{"role": "assistant", "content": gradio_welcome_text()}], s, cleared
    clear.click(on_clear, inputs=None, outputs=[chatbot, state, msg])

demo.launch()
