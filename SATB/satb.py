import gradio as gr
from SATB.llm import LLM
from SATB.pdf import *

prompt = """
Take the text following "---START---" is extracted from a pdf file and provides information about a security advisory.
Please extract the steps necessary to fix the issue.
Then write them down in Json Format like this:
{
    "mentioned_cpes": [...],
    "issue_name": "...",
    "steps_to_fix": {
        "1": {
            "depends_on_steps": [2,3]
            "command": "service apache2 stop"
            "description": "Stop the apache webserver"
        }
    }
}

Mentioned_cpes and issue_name you also get from the text.
For every step should be a command either create by you or written in the text.

---START---

"""


class SATB:
    initDone = False

    def __init__(self):
        self.llm = LLM()

        self.initDone = True

    def ask_pdf(self, file) -> str:
        feedback = self.llm.ask(prompt + pdf_to_text(file))
        print(feedback)
        return feedback.content##.replace("\n","<br>")

    def run(self):
        demo = gr.Interface(fn=self.ask_pdf, inputs="file", outputs="text")
        demo.launch()
