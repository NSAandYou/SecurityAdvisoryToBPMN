import json
import random
import string

BASE_POINT_X = 500
BASE_POINT_Y = 500
BASE_POINT_W = 100
BASE_POINT_H = 100
BASE_ADD_X = 200


def generate_string_id(size: int = 7) -> str:
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(size))


# indent text block for better look
def inline(text: str, spaces: int = 2):
    inline_str = " " * spaces
    return_value = text.strip("\n").replace("\n", "\n" + inline_str)
    if return_value == "":
        return ""
    else:
        return inline_str + return_value


def to_dict(json_string: str) -> dict:
    return json.loads(json_string)


# repairs dict from llm on basic level
def repair_dict(d: dict):
    if "mentioned_cpes" not in d:
        d["mentioned_cpes"] = []
    if "issue_name" not in d:
        d["issue_name"] = "UNKNOWN"
    if "steps_to_fix" not in d:
        raise Exception("ERROR: JSON not repairable.")

    for key, values in d["steps_to_fix"].items():
        if "command" not in values:
            values["command"] = []
        if "description" not in values:
            values["description"] = ""
        if "depends_on_steps" not in values:
            values["depends_on_steps"] = []
    return d


# expends dict for later use
def advance_dict(d: dict) -> dict:
    d["process_id"] = f"Process_{generate_string_id()}"

    # Add Start Element
    d["steps_to_fix"] = {'0': {
        'element_id': 'StartEvent_1',
        'element_type': 'start',
        'depends_on_steps': []
    }} | d["steps_to_fix"]

    # Translates paths into depends_on_steps for later processing
    for path_key, path in d["paths"].items():
        for index in range(1, len(path)):
            step_keys = path[index]
            if isinstance(step_keys, list):
                for step_key in step_keys:
                    if isinstance(path[index - 1], list):
                        d["steps_to_fix"][str(step_key)]['depends_on_steps'].extend(path[index - 1])
                    else:
                        d["steps_to_fix"][str(step_key)]['depends_on_steps'].append(path[index - 1])
            else:
                if isinstance(path[index - 1], list):
                    d["steps_to_fix"][str(step_keys)]['depends_on_steps'].extend(path[index - 1])
                else:
                    d["steps_to_fix"][str(step_keys)]['depends_on_steps'].append(path[index - 1])

    for key, values in d["steps_to_fix"].items():
        # Add element_id, required for later steps, element_type
        values['element_id'] = f"Activity_{generate_string_id()}"
        values['required_for_steps'] = []
        values['flows'] = {'in': {}, 'out': {}}
        if 'element_type' not in values:
            values['element_type'] = "task"

        # Add Start element as dependency
        if not values['depends_on_steps'] and key != '0':
            values['depends_on_steps'] = [0]

        # Fill required_for_steps
        for index, depend in enumerate(values['depends_on_steps']):
            depend = values['depends_on_steps'][index] = str(depend)
            d["steps_to_fix"][depend]['required_for_steps'].append(key)

    # Add end element
    d["steps_to_fix"] = d["steps_to_fix"] | {'9999': {
        'element_id': f'Event_{generate_string_id()}',
        'element_type': 'end',
        'depends_on_steps': [key for key, values in d["steps_to_fix"].items() if not values['required_for_steps']],
        'required_for_steps': [],
        'flows': {'in': {}, 'out': {}}
    }}

    # Make all steps 'useless' so for required for end
    for key, values in d["steps_to_fix"].items():
        if not values['required_for_steps'] and key != '9999':
            values['required_for_steps'] = ['9999']

    d = advance_dict_gateway(d)

    # Fill flows
    for key, values in d["steps_to_fix"].items():
        for following_step in values['required_for_steps']:
            flow_id = f'Flow_{generate_string_id()}'
            values['flows']['out'][flow_id] = following_step
            d["steps_to_fix"][following_step]['flows']['in'][flow_id] = key

    d = advance_dict_coor(d)

    return d


def advance_dict_coor(d: dict) -> dict:
    done = False

    # Define start coordinates
    for key, value in d['steps_to_fix'].items():
        if value['element_type'] in ['start', 'end']:
            value['coor'] = {
                'x': BASE_POINT_X,
                'y': BASE_POINT_Y,
                'w': BASE_POINT_W // 3,
                'h': BASE_POINT_H // 3,
            }
        elif value['element_type'] == 'task':
            value['coor'] = {
                'x': BASE_POINT_X,
                'y': BASE_POINT_Y,
                'w': BASE_POINT_W,
                'h': BASE_POINT_H,
            }
        elif value['element_type'].startswith("gate_"):
            value['coor'] = {
                'x': BASE_POINT_X,
                'y': BASE_POINT_Y,
                'w': BASE_POINT_W // 2,
                'h': BASE_POINT_H // 2,
            }
        else:
            print("JSON-TO-XML Coordinates: Element Typ unknown")

    # sort all elements on the x-axis based on required_for_steps
    while not done:
        done = True
        for step, value in d['steps_to_fix'].items():
            for following_step in value['required_for_steps']:
                if value['coor']['x'] >= d['steps_to_fix'][following_step]['coor']['x']:
                    d['steps_to_fix'][following_step]['coor']['x'] += BASE_ADD_X
                    done = False

    lines = {}
    min_y = BASE_POINT_Y
    max_y = BASE_POINT_Y

    # separate the x values into lines.
    for step, value in d['steps_to_fix'].items():
        x = value['coor']['x']
        line_key = (x - BASE_POINT_X) // BASE_ADD_X
        if line_key not in lines:
            lines[line_key] = [step]
        else:
            lines[line_key].append(step)

    # Define y coor first try by averaging the line before
    for index, line in lines.items():
        for step in line:
            s = 0
            c = 0
            for dependency in d['steps_to_fix'][step]['depends_on_steps']:
                s += d['steps_to_fix'][dependency]['coor']['y']
                c += 1
            if c == 0:
                d['steps_to_fix'][step]['coor']['y'] = BASE_POINT_Y
            else:
                d['steps_to_fix'][step]['coor']['y'] = s // c

        # Change y so nothing overlaps
        done = False
        while not done:
            done = True
            for step in line:
                for walker in line:
                    if step != walker and abs(
                            d['steps_to_fix'][step]['coor']['y'] - d['steps_to_fix'][walker]['coor']['y']) < 200:
                        d['steps_to_fix'][step]['coor']['y'] += 200
                        done = False
                if d['steps_to_fix'][step]['coor']['y'] > max_y:
                    max_y = d['steps_to_fix'][step]['coor']['y']
                elif d['steps_to_fix'][step]['coor']['y'] < min_y:
                    min_y = d['steps_to_fix'][step]['coor']['y']

        # Finally adjust start and end
        d['steps_to_fix']['0']['coor']['y'] = (min_y + max_y) // 2
        d['steps_to_fix']['9999']['coor']['y'] = (min_y + max_y) // 2

    return d


# adds gates(exclusive) if necessary (starting with step_id 10001)
def advance_dict_gateway(d: dict) -> dict:
    gatekey = 10000
    gateways = {}
    for key, value in d['steps_to_fix'].items():
        # if step is required for multiple other steps create exclusive(split) gate
        if len(value['required_for_steps']) > 1:
            gatekey += 1
            gateways[str(gatekey)] = {
                'element_id': f'Gateway_{generate_string_id()}',
                'element_type': 'gate_split',
                'depends_on_steps': [key],
                'required_for_steps': value['required_for_steps'],
                'flows': {'in': {}, 'out': {}}
            }

            # make all following steps refer to exclusive(split) gate
            for required_for_key in value['required_for_steps']:
                if required_for_key in d['steps_to_fix']:
                    d['steps_to_fix'][required_for_key]['depends_on_steps'] = [step if step != key else str(gatekey) for
                                                                               step in
                                                                               d['steps_to_fix'][required_for_key][
                                                                                   'depends_on_steps']]

            value['required_for_steps'] = [str(gatekey)]

        # if step depends on multiple other steps create exclusive(unite) gate
        if len(value['depends_on_steps']) > 1:
            gatekey += 1
            gateways[str(gatekey)] = {
                'element_id': f'Gateway_{generate_string_id()}',
                'element_type': 'gate_unite',
                'depends_on_steps': value['depends_on_steps'],
                'required_for_steps': [key],
                'flows': {'in': {}, 'out': {}}
            }

            # make all previous steps refer to exclusive(unite) gate
            for depends_on_key in value['depends_on_steps']:
                if depends_on_key in d['steps_to_fix']:
                    d['steps_to_fix'][depends_on_key]['required_for_steps'] = [step if step != key else str(gatekey) for
                                                                               step in
                                                                               d['steps_to_fix'][depends_on_key][
                                                                                   'required_for_steps']]

            value['depends_on_steps'] = [str(gatekey)]

    # add gates to the usual steps
    d['steps_to_fix'] = d['steps_to_fix'] | gateways

    return d


def add_element_flows(content: dict) -> str:
    text = ""
    for key in content['in']:
        text += f"<bpmn:incoming>{key}</bpmn:incoming>\n"
    for key in content['out']:
        text += f"<bpmn:outgoing>{key}</bpmn:outgoing>\n"
    return text


def generate_all_element_flows(steps_dict: dict) -> str:
    text = ""
    for key, value in steps_dict.items():
        for flow_id, target in value['flows']['out'].items():
            text += f"""<bpmn:sequenceFlow id="{flow_id}" sourceRef="{value['element_id']}" targetRef="{steps_dict[target]['element_id']}" />\n"""
    return text


def generate_element_task(element_id: str, content: dict) -> str:
    return f"""<bpmn:task id="{element_id}" name="{content['command']}">
{inline(add_element_flows(content['flows']))}
</bpmn:task>"""


def generate_element_start(element_id: str, content: dict) -> str:
    return f"""<bpmn:startEvent id="{element_id}" name="Start Patch">
{inline(add_element_flows(content['flows']))}
</bpmn:startEvent>"""


def generate_element_end(element_id: str, content: dict) -> str:
    return f"""<bpmn:endEvent id="{element_id}" name="Finished Patch">
{inline(add_element_flows(content['flows']))}
</bpmn:endEvent>"""


def generate_element_gate(element_id: str, content: dict, split_gate: bool) -> str:
    return f"""<bpmn:exclusiveGateway id="{element_id}" name="{"Split" if split_gate else "Unite"}">
{inline(add_element_flows(content['flows']))}
</bpmn:exclusiveGateway>"""


# generate the bpmn-file string
def generate_xml(process_dict: dict) -> str:
    process_id = process_dict['process_id']
    process_name = process_dict['issue_name']

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:modeler="http://camunda.org/schema/modeler/1.0" xmlns:camunda="http://camunda.org/schema/1.0/bpmn" id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn" exporter="Camunda Web Modeler" exporterVersion="ac436f7" modeler:executionPlatform="Camunda Cloud" modeler:executionPlatformVersion="8.5.0" camunda:diagramRelationId="0994b581-395e-4bc1-b247-0453712fbfe1">
  <bpmn:process id="{process_id}" name="{process_name}" isExecutable="true">
{inline(generate_xml_body_process(process_dict["steps_to_fix"]), 4)}
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="{process_id}">
{inline(generate_xml_body_diagram(process_dict["steps_to_fix"]), 6)}
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>"""


# add the xml process part of a BPMN-file containing the objects
def generate_xml_body_process(steps_dict: dict) -> str:
    body_text = ""
    for step, value in steps_dict.items():
        if value['element_type'] == 'task':
            body_text += generate_element_task(element_id=value['element_id'], content=value) + "\n"
        elif value['element_type'] == 'start':
            body_text += generate_element_start(element_id=value['element_id'], content=value) + "\n"
        elif value['element_type'] == 'end':
            body_text += generate_element_end(element_id=value['element_id'], content=value) + "\n"
        elif value['element_type'] == 'gate_split':
            body_text += generate_element_gate(element_id=value['element_id'], content=value, split_gate=True) + "\n"
        elif value['element_type'] == 'gate_unite':
            body_text += generate_element_gate(element_id=value['element_id'], content=value, split_gate=False) + "\n"
        else:
            print("JSON-TO-XML: Element Typ unknown")
    body_text += generate_all_element_flows(steps_dict)
    return body_text


# add the xml body part of a BPMN-file containing the positions
def generate_xml_body_diagram(steps_dict: dict) -> str:
    body_text = ""
    for step, value in steps_dict.items():
        body_text += f"""<bpmndi:BPMNShape id="{value['element_id']}_di" bpmnElement="{value['element_id']}">
  <dc:Bounds x="{value['coor']['x']}" y="{value['coor']['y']}" width="{value['coor']['w']}" height="{value['coor']['h']}" />
</bpmndi:BPMNShape>
"""
        for flow_id, target in value['flows']['out'].items():
            if value['coor']['y'] + value['coor']['h'] // 2 == steps_dict[target]['coor']['y'] + \
                    steps_dict[target]['coor']['h'] // 2:
                body_text += f"""<bpmndi:BPMNEdge id="{flow_id}_di" bpmnElement="{flow_id}">
  <di:waypoint x="{value['coor']['x'] + value['coor']['w']}" y="{value['coor']['y'] + value['coor']['h'] // 2}" />
  <di:waypoint x="{steps_dict[target]['coor']['x']}" y="{steps_dict[target]['coor']['y'] + steps_dict[target]['coor']['h'] // 2}" />
</bpmndi:BPMNEdge>
"""
            else:
                body_text += f"""<bpmndi:BPMNEdge id="{flow_id}_di" bpmnElement="{flow_id}">
  <di:waypoint x="{value['coor']['x'] + value['coor']['w']}" y="{value['coor']['y'] + value['coor']['h'] // 2}" />
  <di:waypoint x="{(value['coor']['x'] + value['coor']['w'] + steps_dict[target]['coor']['x']) // 2}" y="{value['coor']['y'] + value['coor']['h'] // 2}" />
  <di:waypoint x="{(value['coor']['x'] + value['coor']['w'] + steps_dict[target]['coor']['x']) // 2}" y="{steps_dict[target]['coor']['y'] + steps_dict[target]['coor']['h'] // 2}" />
  <di:waypoint x="{steps_dict[target]['coor']['x']}" y="{steps_dict[target]['coor']['y'] + steps_dict[target]['coor']['h'] // 2}" />
</bpmndi:BPMNEdge>
"""

    return body_text


# takes raw_json in form of a string and return bpmn-file string
def raw_json_to_bpmn_xml(raw_json: str) -> str:
    return generate_xml(advance_dict(repair_dict(to_dict(raw_json))))
