import gradio as gr
from datetime import datetime
import os

from SATB.llm import LLM
from SATB.container_extractor import *
from SATB.json_to_xml import raw_json_to_bpmn_xml

prompt = """
Take the text following "---START---" provides information from a security advisory.
Please extract the steps necessary to fix the issue. If there is a workaround take the steps of the workaround.
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

For every step should be a command either create by you or written in the text.
depends_on_steps and description is are necessary fields.

---START---

"""


def create_folder() -> str:
    creation_name = "created_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    os.makedirs(creation_name)
    return os.path.join(os.path.dirname(os.path.abspath(creation_name)), creation_name)


class SATB:
    initDone = False

    def __init__(self):
        self.llm = LLM()

        self.initDone = True

    def ask_llm(self, advisory_text) -> str:
        answer = self.llm.ask(prompt + advisory_text).content
        return answer[answer.index("{"):answer.rfind("}")+1]

    def process_input(self, input_string: str) -> str:
        folder_path = create_folder()

        errors = []

        input_string = input_string.split("\n")

        counter_success = 0
        for advisory in input_string:
            try:
                feedback_json = self.ask_llm(given_advisory_to_text(advisory))
                advisory_name = advisory.replace("/", "_").replace(":", "_").replace(".pdf", "")
                with open(os.path.join(folder_path, advisory_name + ".json"), "w") as file:
                    file.write(feedback_json)
                bpmn_xml = raw_json_to_bpmn_xml(feedback_json)
                with open(os.path.join(folder_path, advisory_name + ".xml"), "w") as file:
                    file.write(bpmn_xml)
                counter_success += 1
            except Exception as e:
                errors.append(str(e))

        output_string = f"File creation finished. {counter_success}/{len(input_string)} could be processed.\nYou can find the files in the folder {folder_path}"
        if errors:
            output_string += "\n\nErrors while processing:\n" + "\n".join(errors)
        return output_string

    def run(self):
        interface = gr.Interface(
            fn=self.process_input,
            inputs="text",
            outputs="text",
            title="Security Advisories to BPMN-FILE",
            description="Just insert the Security Advisory Path into the text field. You can insert multiple at the same time using multiple lines.",
        )
        interface.launch()
