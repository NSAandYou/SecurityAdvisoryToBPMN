import json, random, string

BASE_POINT_X = 500
BASE_POINT_Y = 500
BASE_POINT_W = 100
BASE_POINT_H = 100
BASE_ADD_X = 200


def generate_string_id(size: int = 7) -> str:
    return ''.join(random.choice(string.ascii_lowercase) for i in range(size))


def inline(text: str, spaces: int = 2):
    inline_str = " " * spaces
    return_value = text.strip("\n").replace("\n", "\n" + inline_str)
    if return_value == "":
        return ""
    else:
        return inline_str + return_value


def to_dict(json_string: str) -> dict:
    return json.loads(json_string)


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


def advance_dict(d: dict) -> dict:
    d["process_id"] = f"Process_{generate_string_id()}"

    ##Add Start Element
    d["steps_to_fix"] = {'0': {
        'element_id': 'StartEvent_1',
        'element_type': 'start',
        'depends_on_steps': []
    }} | d["steps_to_fix"]

    for key, values in d["steps_to_fix"].items():
        ## Add element_id, required for later steps, element_type
        values['element_id'] = f"Activity_{generate_string_id()}"
        values['required_for_steps'] = []
        values['flows'] = {'in': {}, 'out': {}}
        if 'element_type' not in values:
            values['element_type'] = "task"

        ## Add Start element as dependency
        if not values['depends_on_steps'] and key != '0':
            values['depends_on_steps'] = [0]

        ## Fill required for later steps list
        for index, depend in enumerate(values['depends_on_steps']):
            depend = values['depends_on_steps'][index] = str(depend)
            d["steps_to_fix"][depend]['required_for_steps'].append(key)

    d["steps_to_fix"] = d["steps_to_fix"] | {'9999': {
        'element_id': f'Event_{generate_string_id()}',
        'element_type': 'end',
        'depends_on_steps': [key for key, values in d["steps_to_fix"].items() if not values['required_for_steps']],
        'required_for_steps': [],
        'flows': {'in': {}, 'out': {}}
    }}

    for key, values in d["steps_to_fix"].items():
        if not values['required_for_steps'] and key != '9999':
            values['required_for_steps'] = ['9999']

    ## Fill flows
    for key, values in d["steps_to_fix"].items():
        for following_step in values['required_for_steps']:
            flow_id = f'Flow_{generate_string_id()}'
            values['flows']['out'][flow_id] = following_step
            d["steps_to_fix"][following_step]['flows']['in'][flow_id] = key

    d = advance_dict_coor(d)

    return d


def advance_dict_coor(d: dict) -> dict:
    done = False

    ## Define x coor
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
        else:
            print("JSON-TO-XML Coordinates: Element Typ unknown")

    while not done:
        done = True
        for step, value in d['steps_to_fix'].items():
            for following_step in value['required_for_steps']:
                if value['coor']['x'] >= d['steps_to_fix'][following_step]['coor']['x']:
                    d['steps_to_fix'][following_step]['coor']['x'] += BASE_ADD_X
                    done = False

    lines = {}

    for step, value in d['steps_to_fix'].items():
        x = value['coor']['x']
        line_key = (x - BASE_POINT_X) // BASE_ADD_X
        if line_key not in lines:
            lines[line_key] = [step]
        else:
            lines[line_key].append(step)

    ## Define y coor first try
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

        ## Change y so nothing overlaps
        done = False
        while not done:
            done = True
            for step in line:
                for walker in line:
                    if step != walker and abs(
                            d['steps_to_fix'][step]['coor']['y'] - d['steps_to_fix'][walker]['coor']['y']) < 200:
                        d['steps_to_fix'][step]['coor']['y'] += 200
                        done = False

        ## Finally adjust start
        s = 0
        c = 0
        for following_step in d['steps_to_fix']['0']['required_for_steps']:
            s += d['steps_to_fix'][following_step]['coor']['y']
            c += 1
        d['steps_to_fix']['0']['coor']['y'] = s // c

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
    return f"""<bpmn:startEvent id="{element_id}">
{inline(add_element_flows(content['flows']))}
</bpmn:startEvent>"""


def generate_element_end(element_id: str, content: dict) -> str:
    return f"""<bpmn:endEvent id="{element_id}">
{inline(add_element_flows(content['flows']))}
</bpmn:endEvent>"""


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


def generate_xml_body_process(steps_dict: dict) -> str:
    body_text = ""
    for step, value in steps_dict.items():
        if value['element_type'] == 'task':
            body_text += generate_element_task(element_id=value['element_id'], content=value) + "\n"
        elif value['element_type'] == 'start':
            body_text += generate_element_start(element_id=value['element_id'], content=value) + "\n"
        elif value['element_type'] == 'end':
            body_text += generate_element_end(element_id=value['element_id'], content=value) + "\n"
        else:
            print("JSON-TO-XML: Element Typ unknown")
    body_text += generate_all_element_flows(steps_dict)
    return body_text


def generate_xml_body_diagram(steps_dict: dict) -> str:
    body_text = ""
    for step, value in steps_dict.items():
        body_text += f"""<bpmndi:BPMNShape id="{value['element_id']}_di" bpmnElement="{value['element_id']}">
  <dc:Bounds x="{value['coor']['x']}" y="{value['coor']['y']}" width="{value['coor']['w']}" height="{value['coor']['h']}" />
</bpmndi:BPMNShape>
"""
        for flow_id, target in value['flows']['out'].items():
            if value['coor']['y'] + value['coor']['h'] // 2 == steps_dict[target]['coor']['y'] + steps_dict[target]['coor']['h'] // 2:
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


def raw_json_to_bpmn_xml(raw_json: str) -> str:
    return generate_xml(advance_dict(repair_dict(to_dict(raw_json))))