import json
import random
import string
from enum import Enum

# Diagram sizes and points
BASE_POINT_X = 160
BASE_POINT_Y = 0
BASE_POINT_W = 100
BASE_POINT_H = 100
BASE_ADD_X = 200
TASK_WIDTH = 120
TASK_HEIGHT = 60
SQUARE_ELEMENTS_SIZE = 40
BASE_GAP_SIZE = 20


# Different kinds of diagram objects
class ElementType(Enum):
    START = 1
    END = 2
    GATEWAY = 3
    SUBPROCESS = 4
    TASK = 5
    FLOW = 6


# generates random string for ids
def generate_string_id(size: int = 7) -> str:
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(size))


# indent text block for better look
def inline(text: str, spaces: int = 2, no_next_line: bool = True):
    inline_str = " " * spaces
    return_value = text.strip("\n").replace("\n", "\n" + inline_str)
    if return_value == "":
        return ""
    else:
        return inline_str + return_value + ("" if no_next_line else "\n")


# string to python dict
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
    return d


# expends dict for later use
def advance_dict(d: dict) -> dict:
    d["process_id"] = f"Process_{generate_string_id()}"

    for task in d['steps_to_fix'].values():
        task['element_id'] = f'Activity_{generate_string_id()}'

    d['subprocesses'] = {}

    for key, path in d['paths'].items():
        d['subprocesses'][key] = {
            'element_id': f'Activity_{generate_string_id()}',
            'element_type': ElementType.SUBPROCESS,
        }
        for step_line in range(len(path)):
            if not isinstance(d['paths'][key][step_line], list):
                d['paths'][key][step_line] = [d['paths'][key][step_line]]
            for step_index in range(len(d['paths'][key][step_line])):
                d['paths'][key][step_line][step_index] = str(d['paths'][key][step_line][step_index])

    d['flows'] = {}
    d['flows_inverse'] = {}

    d['coordinates'] = []

    return d


# adds elements to the coordinates list to be used later
def add_to_coordinates(d: dict, element_id: str, element_type: ElementType, subprocess: str = None):
    d['coordinates'].append({
        'element_id': element_id,
        'element_type': element_type,
        'subprocess': subprocess,
        'coordinates': {
            'x': 0,
            'y': 0,
            'width': 0,
            'height': 0
        }
    })


# fill in the right coordinates for elements in the list
def calculate_coordinates(d: dict):
    max_width = 0
    x = BASE_POINT_X + 2 * (SQUARE_ELEMENTS_SIZE + 2 * BASE_GAP_SIZE)
    y = BASE_POINT_Y

    # Subprocesses
    for sub_key, sub in d['subprocesses'].items():
        sub_width = 0
        sub_height = 0
        # Subprocess
        for element in [e['coordinates'] for e in d['coordinates'] if e['element_id'] == sub['element_id']]:
            element['x'] = x
            element['y'] = y
            element['width'] = sub_width = 4 * SQUARE_ELEMENTS_SIZE + 5 * BASE_GAP_SIZE + (TASK_WIDTH + BASE_GAP_SIZE) * max([len(p) for p in d['paths'].values()])
            element['height'] = sub_height = BASE_GAP_SIZE + (TASK_HEIGHT + BASE_GAP_SIZE) * max([len(p) for p in d['paths'][sub_key]])

        # Sub Start
        for element in [e['coordinates'] for e in d['coordinates'] if e['element_id'] == f'Activity_{sub_key}AAAAAA']:
            element['x'] = x + BASE_GAP_SIZE
            element['y'] = y + sub_height // 2 - SQUARE_ELEMENTS_SIZE // 2
            element['width'] = SQUARE_ELEMENTS_SIZE
            element['height'] = SQUARE_ELEMENTS_SIZE

        # Sub End
        for element in [e['coordinates'] for e in d['coordinates'] if e['element_id'] == f'Activity_{sub_key}ZZZZZZ']:
            element['x'] = x + sub_width - BASE_GAP_SIZE - SQUARE_ELEMENTS_SIZE
            element['y'] = y + sub_height // 2 - SQUARE_ELEMENTS_SIZE // 2
            element['width'] = SQUARE_ELEMENTS_SIZE
            element['height'] = SQUARE_ELEMENTS_SIZE

        # Sub Start Gate
        for element in [e['coordinates'] for e in d['coordinates'] if e['element_id'] == f'Gateway_{sub_key}BBBBBB']:
            element['x'] = x + 2*BASE_GAP_SIZE + SQUARE_ELEMENTS_SIZE
            element['y'] = y + sub_height // 2 - SQUARE_ELEMENTS_SIZE // 2
            element['width'] = SQUARE_ELEMENTS_SIZE
            element['height'] = SQUARE_ELEMENTS_SIZE

        # Sub End Gate
        for element in [e['coordinates'] for e in d['coordinates'] if e['element_id'] == f'Gateway_{sub_key}YYYYYY']:
            element['x'] = x + sub_width - 2*(BASE_GAP_SIZE + SQUARE_ELEMENTS_SIZE)
            element['y'] = y + sub_height // 2 - SQUARE_ELEMENTS_SIZE // 2
            element['width'] = SQUARE_ELEMENTS_SIZE
            element['height'] = SQUARE_ELEMENTS_SIZE

        # Tasks
        for step_line_index, step_line in enumerate(d['paths'][sub_key]):
            for step_index, step_key in enumerate(step_line):
                step = d['steps_to_fix'][step_key]
                element = [e['coordinates'] for e in d['coordinates'] if e['element_id'] == step['element_id']][0]
                element['x'] = x + BASE_GAP_SIZE + 2 * (SQUARE_ELEMENTS_SIZE + BASE_GAP_SIZE) + step_line_index * (TASK_WIDTH + BASE_GAP_SIZE)
                element['y'] = y + BASE_GAP_SIZE + (len(step_line) - (step_index + 1)) * (TASK_HEIGHT + BASE_GAP_SIZE)
                element['width'] = TASK_WIDTH
                element['height'] = TASK_HEIGHT
        y += sub_height + BASE_GAP_SIZE
        max_width = sub_width if sub_width > max_width else max_width

    # Start
    for element in [e['coordinates'] for e in d['coordinates'] if e['element_id'] == f'Activity_AAAAAAA']:
        element['x'] = BASE_POINT_X
        element['y'] = BASE_POINT_Y + (y - BASE_GAP_SIZE) // 2 - SQUARE_ELEMENTS_SIZE // 2
        element['width'] = SQUARE_ELEMENTS_SIZE
        element['height'] = SQUARE_ELEMENTS_SIZE

    # End
    for element in [e['coordinates'] for e in d['coordinates'] if e['element_id'] == f'Activity_ZZZZZZZ']:
        element['x'] = BASE_POINT_X + 4 * (SQUARE_ELEMENTS_SIZE + 2 * BASE_GAP_SIZE) + max_width - SQUARE_ELEMENTS_SIZE
        element['y'] = BASE_POINT_Y + (y - BASE_GAP_SIZE) // 2 - SQUARE_ELEMENTS_SIZE // 2
        element['width'] = SQUARE_ELEMENTS_SIZE
        element['height'] = SQUARE_ELEMENTS_SIZE

    # Start Gate
    for element in [e['coordinates'] for e in d['coordinates'] if e['element_id'] == f'Gateway_BBBBBBB']:
        element['x'] = BASE_POINT_X + SQUARE_ELEMENTS_SIZE + 2 * BASE_GAP_SIZE
        element['y'] = BASE_POINT_Y + (y - BASE_GAP_SIZE) // 2 - SQUARE_ELEMENTS_SIZE // 2
        element['width'] = SQUARE_ELEMENTS_SIZE
        element['height'] = SQUARE_ELEMENTS_SIZE

    # End Gate
    for element in [e['coordinates'] for e in d['coordinates'] if e['element_id'] == f'Gateway_YYYYYYY']:
        element['x'] = BASE_POINT_X + 4 * (SQUARE_ELEMENTS_SIZE + 2 * BASE_GAP_SIZE) + max_width - SQUARE_ELEMENTS_SIZE - 2 * BASE_GAP_SIZE - SQUARE_ELEMENTS_SIZE
        element['y'] = BASE_POINT_Y + (y - BASE_GAP_SIZE) // 2 - SQUARE_ELEMENTS_SIZE // 2
        element['width'] = SQUARE_ELEMENTS_SIZE
        element['height'] = SQUARE_ELEMENTS_SIZE

    # Flows
    for element in [e for e in d['coordinates'] if e['element_type'] == ElementType.FLOW]:
        target_ids = d['flows'][element['element_id']].values()
        target_coordinates = [e for e in d['coordinates'] if e['element_id'] in target_ids]

        if target_coordinates[0]['coordinates']['x'] < target_coordinates[1]['coordinates']['x']:
            source_element = target_coordinates[0]
            target_element = target_coordinates[1]
        else:
            target_element = target_coordinates[0]
            source_element = target_coordinates[1]

        # Should different edge be used for source element?
        # Yes
        if source_element['element_type'] == ElementType.GATEWAY and abs(source_element['coordinates']['y'] - target_element['coordinates']['y']) > BASE_GAP_SIZE*4:
            element['coordinates']['x'] = source_element['coordinates']['x'] + source_element['coordinates']['width'] // 2
            element['coordinates']['y'] = source_element['coordinates']['y'] + (source_element['coordinates']['height'] if source_element['coordinates']['y'] < target_element['coordinates']['y'] else 0)
        # No
        else:
            element['coordinates']['x'] = source_element['coordinates']['x'] + source_element['coordinates']['width']
            element['coordinates']['y'] = source_element['coordinates']['y'] + source_element['coordinates']['height'] // 2

        # Should different edge be used for target element?
        # Yes
        if target_element['element_type'] == ElementType.GATEWAY and abs(source_element['coordinates']['y'] - target_element['coordinates']['y']) > BASE_GAP_SIZE*4:
            element['coordinates']['width'] = target_element['coordinates']['x'] + target_element['coordinates']['width'] // 2
            element['coordinates']['height'] = target_element['coordinates']['y'] + (target_element['coordinates']['height'] if source_element['coordinates']['y'] > target_element['coordinates']['y'] else 0)

        # No
        else:
            element['coordinates']['width'] = target_element['coordinates']['x']
            element['coordinates']['height'] = target_element['coordinates']['y'] + target_element['coordinates']['height'] // 2

        # Waypoints
        element['coordinates']['waypoints'] = []

        # No Waypoint
        if element['coordinates']['y'] == element['coordinates']['height']:
            pass
        # Add one waypoint
        elif abs(source_element['coordinates']['y'] - target_element['coordinates']['y']) > BASE_GAP_SIZE*4:
            # First x or y axis?
            # y
            if source_element['element_type'] == ElementType.GATEWAY:
                element['coordinates']['waypoints'].append([
                    element['coordinates']['x'],
                    element['coordinates']['height']
                ])
            # x
            else:
                element['coordinates']['waypoints'].append([
                    element['coordinates']['width'],
                    element['coordinates']['y']
                ])

        # Add two waypoints
        else:
            element['coordinates']['waypoints'].append([
                (element['coordinates']['x'] + element['coordinates']['width']) // 2,
                element['coordinates']['y']
            ])
            element['coordinates']['waypoints'].append([
                (element['coordinates']['x'] + element['coordinates']['width']) // 2,
                element['coordinates']['height']
            ])


# Adds flows to flow list and returns flow as string for bpmn
def add_element_flows(d: dict, sources: list, targets: list, out: bool) -> str:
    text = ""
    r = "outgoing" if out else "incoming"

    for end_one in sources:
        for end_two in targets:
            if end_one + end_two in d['flows_inverse']:
                key = d['flows_inverse'][end_one + end_two]
            elif end_two + end_one in d['flows_inverse']:
                key = d['flows_inverse'][end_two + end_one]
            else:
                key = f'Flow_{generate_string_id()}'
                d['flows'][key] = {'end_one': end_one, 'end_two': end_two}
                d['flows_inverse'][end_one + end_two] = key
                add_to_coordinates(d, key, ElementType.FLOW)

            text += f"<bpmn:{r}>{key}</bpmn:{r}>\n"
    return text


# generate the bpmn-file string
def generate_xml(process_dict: dict) -> str:
    process_id = process_dict['process_id']
    process_name = process_dict['issue_name']

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:modeler="http://camunda.org/schema/modeler/1.0" xmlns:camunda="http://camunda.org/schema/1.0/bpmn" id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn" exporter="Camunda Web Modeler" exporterVersion="ac436f7" modeler:executionPlatform="Camunda Cloud" modeler:executionPlatformVersion="8.5.0" camunda:diagramRelationId="0994b581-395e-4bc1-b247-0453712fbfe1">
  <bpmn:process id="{process_id}" name="{process_name}" isExecutable="true">
{inline(generate_xml_body_process(process_dict), 4)}
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="{process_id}">
{inline(generate_xml_body_diagram(process_dict), 6)}
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>"""


# add the xml process part of a BPMN-file containing the objects
def generate_xml_body_process(d: dict) -> str:
    body_text = ""

    # Multiple Options for the patch?
    # Yes
    if len(d['subprocesses']) > 1:
        # Start
        body_text += f"""<bpmn:startEvent id="Activity_AAAAAAA" name="Start Patch">
{inline(add_element_flows(d, ['Activity_AAAAAAA'], ['Gateway_BBBBBBB'], True))}
</bpmn:startEvent>\n"""
        add_to_coordinates(d, 'Activity_AAAAAAA', ElementType.START)

        # Start gate
        body_text += f"""<bpmn:exclusiveGateway id="Gateway_BBBBBBB" name="{"Options"}">
{inline(add_element_flows(d, ['Activity_AAAAAAA'], ['Gateway_BBBBBBB'], False))}
{inline(add_element_flows(d, ['Gateway_BBBBBBB'], [sub['element_id'] for sub in d['subprocesses'].values()], True))}
</bpmn:exclusiveGateway>\n"""
        add_to_coordinates(d, 'Gateway_BBBBBBB', ElementType.GATEWAY)

        # End
        body_text += f"""<bpmn:endEvent id="Activity_ZZZZZZZ" name="Finished Patch">
{inline(add_element_flows(d, ['Gateway_YYYYYYY'], ['Activity_ZZZZZZZ'], False))}
</bpmn:endEvent>\n"""
        add_to_coordinates(d, 'Activity_ZZZZZZZ', ElementType.END)

        # End gate
        body_text += f"""<bpmn:exclusiveGateway id="Gateway_YYYYYYY" name="{"Options"}">
{inline(add_element_flows(d, [sub['element_id'] for sub in d['subprocesses'].values()], ['Gateway_YYYYYYY'], False))}
{inline(add_element_flows(d, ['Gateway_YYYYYYY'], ['Activity_ZZZZZZZ'], True))}
</bpmn:exclusiveGateway>\n"""
        add_to_coordinates(d, 'Gateway_YYYYYYY', ElementType.GATEWAY)

    # No
    else:
        # Start
        body_text += f"""<bpmn:startEvent id="Activity_AAAAAAA" name="Start Patch">
{inline(add_element_flows(d, ['Activity_AAAAAAA'], [sub['element_id'] for sub in d['subprocesses'].values()], True))}
</bpmn:startEvent>\n"""
        add_to_coordinates(d, 'Activity_AAAAAAA', ElementType.START)

        # End
        body_text += f"""<bpmn:endEvent id="Activity_ZZZZZZZ" name="Finished Patch">
{inline(add_element_flows(d, [sub['element_id'] for sub in d['subprocesses'].values()], ['Activity_ZZZZZZZ'], False))}
</bpmn:endEvent>\n"""
        add_to_coordinates(d, 'Activity_ZZZZZZZ', ElementType.END)

    # Options (here equal to subprocesses)
    for sub_key, sub in d['subprocesses'].items():
        # Add subprocess itself
        add_to_coordinates(d, sub['element_id'], ElementType.SUBPROCESS, sub_key)
        body_text += f"""<bpmn:subProcess id="{sub['element_id']}">\n"""

        # Add gateway if parallel at the start of this option
        body_text += inline(add_element_flows(
            d,
            ["Gateway_BBBBBBB" if len(d['subprocesses']) > 1 else "Activity_AAAAAAA"],
            [sub['element_id']],
            False
        ), no_next_line=False)

        # Add gateway if parallel at the end of this option
        body_text += inline(add_element_flows(
            d,
            [sub['element_id']],
            ["Gateway_YYYYYYY" if len(d['subprocesses']) > 1 else "Activity_ZZZZZZZ"],
            True), no_next_line=False)

        # Gets paths for this specific option(subprocess)
        path = d['paths'][sub_key]

        # Parallel at start?
        # Yes
        if len(path[0]) > 1:
            # Start
            body_text += inline(f"""<bpmn:startEvent id="Activity_{sub_key}AAAAAA" name="Start Option">
{inline(add_element_flows(d, [f'Activity_{sub_key}AAAAAA'], [f'Gateway_{sub_key}BBBBBB'], True))}
</bpmn:startEvent>\n""", no_next_line=False)
            add_to_coordinates(d, f"Activity_{sub_key}AAAAAA", ElementType.START, sub_key)

            # Start gate
            body_text += inline(f"""<bpmn:exclusiveGateway id="Gateway_{sub_key}BBBBBB" name="{"Parallel"}">
{inline(add_element_flows(d, [f'Activity_{sub_key}AAAAAA'], [f'Gateway_{sub_key}BBBBBB'], False))}
{inline(add_element_flows(d, [f'Gateway_{sub_key}BBBBBB'], [d['steps_to_fix'][element_key]['element_id'] for element_key in path[0]], True))}
</bpmn:exclusiveGateway>\n""", no_next_line=False)
            add_to_coordinates(d, f"Gateway_{sub_key}BBBBBB", ElementType.GATEWAY, sub_key)

        # No
        else:
            body_text += inline(f"""<bpmn:startEvent id="Activity_{sub_key}AAAAAA" name="Start Option">
{inline(add_element_flows(d, [f'Activity_{sub_key}AAAAAA'], [d['steps_to_fix'][element_key]['element_id'] for element_key in path[0]], True))}
</bpmn:startEvent>\n""", no_next_line=False)
            add_to_coordinates(d, f"Activity_{sub_key}AAAAAA", ElementType.START, sub_key)

        # Parallel at end?
        # Yes
        if len(path[len(path) - 1]) > 1:
            # End
            body_text += inline(f"""<bpmn:endEvent id="Activity_{sub_key}ZZZZZZ" name="Finished Option">
{inline(add_element_flows(d, [f'Gateway_{sub_key}YYYYYY'], [f'Activity_{sub_key}ZZZZZZ'], False))}
</bpmn:endEvent>""", no_next_line=False)
            add_to_coordinates(d, f"Activity_{sub_key}ZZZZZZ", ElementType.END, sub_key)

            # End gate
            body_text += inline(f"""<bpmn:exclusiveGateway id="Gateway_{sub_key}YYYYYY" name="{"Parallel"}">
{inline(add_element_flows(d, [f'Gateway_{sub_key}YYYYYY'], [f'Activity_{sub_key}ZZZZZZ'], True))}
{inline(add_element_flows(d, [d['steps_to_fix'][element_key]['element_id'] for element_key in path[len(path) - 1]], [f'Gateway_{sub_key}YYYYYY'], False))}
</bpmn:exclusiveGateway>""", no_next_line=False)
            add_to_coordinates(d, f"Gateway_{sub_key}YYYYYY", ElementType.GATEWAY, sub_key)

        # No
        else:
            body_text += inline(f"""<bpmn:endEvent id="Activity_{sub_key}ZZZZZZ" name="Finished Option">
{inline(add_element_flows(d, [d['steps_to_fix'][element_key]['element_id'] for element_key in path[len(path) - 1]], [f'Activity_{sub_key}ZZZZZZ'], False))}
</bpmn:endEvent>""", no_next_line=False)
            add_to_coordinates(d, f"Activity_{sub_key}ZZZZZZ", ElementType.END, sub_key)

        # Add all tasks of this option
        for step_line_nr in range(len(path)):
            for step in path[step_line_nr]:
                value = d['steps_to_fix'][step]
                body_text += inline(f"""<bpmn:task id="{value['element_id']}" name="{value['command']}">
{inline(add_element_flows(d, ([f'Gateway_{sub_key}BBBBBB'] if len(path[0]) > 1 else [f'Activity_{sub_key}AAAAAA']) if step_line_nr - 1 < 0 else [d['steps_to_fix'][key]['element_id'] for key in path[step_line_nr - 1]], [value['element_id']], False))}
{inline(add_element_flows(d, [value['element_id']], [d['steps_to_fix'][key]['element_id'] for key in path[step_line_nr + 1]] if step_line_nr + 1 < len(path) else ([f'Gateway_{sub_key}YYYYYY'] if len(path[len(path) - 1]) > 1 else [f'Activity_{sub_key}ZZZZZZ']), True))}
</bpmn:task>""", no_next_line=False)
                add_to_coordinates(d, f"{value['element_id']}", ElementType.TASK, sub_key)

        # Close subprocess
        body_text += f"""</bpmn:subProcess>\n"""

    # Add all flow lines
    for flow_key, flow in d['flows'].items():
        body_text += f"""<bpmn:sequenceFlow id="{flow_key}" sourceRef="{flow['end_one']}" targetRef="{flow['end_two']}" />\n"""
    return body_text


# add the xml body part of a BPMN-file containing the positions
def generate_xml_body_diagram(d: dict) -> str:
    # Fill in the right coordinates
    calculate_coordinates(d)

    body_text = ""
    for element in d['coordinates']:
        # Is element a flow line?
        # Yes
        if element['element_type'] == ElementType.FLOW:
            body_text += f"""<bpmndi:BPMNEdge id="{element['element_id']}_di" bpmnElement="{element['element_id']}">
    <di:waypoint x="{element['coordinates']['x']}" y="{element['coordinates']['y']}" />{'' if not element['coordinates']['waypoints'] else "".join([f"""
    <di:waypoint x="{waypoint[0]}" y="{waypoint[1]}" />""" for waypoint in element['coordinates']['waypoints']])}
    <di:waypoint x="{element['coordinates']['width']}" y="{element['coordinates']['height']}" />
</bpmndi:BPMNEdge>
"""
        # No
        else:
            body_text += f"""<bpmndi:BPMNShape id="{element['element_id']}_di" bpmnElement="{element['element_id']}"{' isExpanded="true"' if element['element_type'] == ElementType.SUBPROCESS else ""}>
    <dc:Bounds x="{element['coordinates']['x']}" y="{element['coordinates']['y']}" width="{element['coordinates']['width']}" height="{element['coordinates']['height']}" />
{f"""<bpmndi:BPMNLabel>
  <dc:Bounds x="{element['coordinates']['x']}" y="{element['coordinates']['y']}" width="{element['coordinates']['width']}" height="{element['coordinates']['height']}" />\n</bpmndi:BPMNLabel>
""" if element['element_type'] == ElementType.TASK else ""}</bpmndi:BPMNShape>
"""

    return body_text


# takes raw_json in form of a string and return bpmn-file string
def raw_json_to_bpmn_xml(raw_json: str) -> str:
    return generate_xml(advance_dict(repair_dict(to_dict(raw_json))))
