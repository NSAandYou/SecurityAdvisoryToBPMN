import os
from datetime import datetime

import gradio as gr

from SATB.container_extractor import *
from SATB.json_to_xml import raw_json_to_bpmn_xml
from SATB.llm import LLM

# static prompt presented to the LLM before the security advisory
prompt = """
The text following "---START---" provides information from a security advisory. Please extract the steps necessary to fix the issue. If there is a workaround, extract the steps of the workaround.

Write the extracted information in JSON format as follows:
{
    "mentioned_cpes": [...],
    "issue_name": "...",
    "steps_to_fix": {
        "1": {
            "command": "Stop Apache Server",
            "description": "The apache server has to be stopped in order to do patch the system. This is done via: service apache2 stop"
        },
        "2": {
            "command": "Update system",
            "description": "Update the whole linux server using the command: sudo apt-get update && apt-get upgrade -y"
        },
        ...
    },
    "paths": {
        "1": [1, 2, 3]      // List of step IDs in sequential order for path 1
        "2": [4, [5, 6]]    // List of step IDs in sequential order for path 2 but step 5 and 6 have to be parallel.
    }
}

steps_to_fix: Enumerate each atomic step necessary for mitigation/fix. Each step should include a command and description.
paths: Enumerate each set of sequential steps which represent different options to fix the issue. The order in the list represents the order mentioned in the advisory.
    - If steps within a path must be executed in parallel, use a nested list structure (e.g., [ [1, 2], 3 ] means steps 1 and 2 are parallel and followed by step 3).
    - Do not use a nested list for a single step; steps should only be nested if they are explicitly parallel.
    - Paths represent one way to fix the issue and so everything should be fixed after running the steps in one path.
    - Every step should be mentioned in at least one path.

Instructions for Extraction:

1. Identify all steps for both the workaround and the fix.
2. Each step should be unique and assigned a number in steps_to_fix.
3. In paths, list the step numbers sequentially.
4. Use nested lists only for steps that must be executed in parallel, based on explicit instructions in the advisory.

Security Advisory Text:
---START---

"""


# creates folder for the output
def create_folder() -> str:
    creation_name = "created_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    os.makedirs(creation_name)
    return os.path.join(os.path.dirname(os.path.abspath(creation_name)), creation_name)


# SATB - Security Advisory to BPMN
class SATB:
    initDone = False

    # initialize LLM
    def __init__(self):
        self.llm = LLM()

        self.initDone = True

    def ask_llm(self, advisory_text) -> str:
        answer = self.llm.ask(prompt + advisory_text).content
        return answer[answer.index("{"):answer.rfind("}")+1]

    # methode called, when submit is pressed in the interface
    # creates folder, searches for the security advisories, converts them to BPMN and saves them
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
                print(f"{counter_success} advisories successfully processed.")
            except Exception as e:
                errors.append(str(e))
                print(str(e))

        output_string = f"File creation finished. {counter_success}/{len(input_string)} could be processed.\nYou can find the files in the folder {folder_path}"
        if errors:
            output_string += "\n\nErrors while processing:\n" + "\n".join(errors)
        return output_string

    # run web interface using gradio
    def run(self):
        interface = gr.Interface(
            fn=self.process_input,
            inputs="text",
            outputs="text",
            title="Security Advisories to BPMN-FILE",
            description="Just insert the Security Advisory Path into the text field. You can insert multiple at the same time using multiple lines.",
        )
        interface.launch()
