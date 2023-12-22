from flask import Flask, request, jsonify
import xml.etree.ElementTree as ET
from dateutil import parser
import json
import re


app = Flask(__name__)

def convert_json_to_dict(json_data):
    try:
        data_dict = json_data
        if not isinstance(data_dict, dict):
            raise ValueError("Invalid JSON format: the top-level structure must be an object.")

        return data_dict
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON: {str(e)}")

def xml_to_dict(element):
    result = {}
    for child in element:
        if child:
            child_dict = xml_to_dict(child)
            if child.tag in result:
                if type(result[child.tag]) is list:
                    result[child.tag].append(child_dict)
                else:
                    result[child.tag] = [result[child.tag], child_dict]
            else:
                result[child.tag] = child_dict
        elif child.text:
            result[child.tag] = child.text
    return result

def normalize_date(date_str):
    try:
        parsed_date = parser.parse(date_str, dayfirst=True, fuzzy=True)
        normalized_date = parsed_date.strftime("%d.%m.%Y")

        return normalized_date
    except Exception as e:
        raise ValueError(f"Error normalizing date: {str(e)}")

def normalize_duration(duration_str):
    try:
        matches = re.findall(r'(\d+)\s*([гндм])', duration_str, re.IGNORECASE)
        if not matches:
            raise ValueError("Invalid duration format.")

        normalized_duration = [0, 0, 0, 0]

        for value, unit in matches:
            unit = unit.lower()

            if unit == 'г':
                normalized_duration[0] += int(value)
            elif unit == 'м':
                normalized_duration[1] += int(value)
            elif unit == 'н':
                normalized_duration[2] += int(value)
            elif unit == 'д':
                normalized_duration[3] += int(value)
            else:
                raise ValueError(f"Invalid time unit: {unit}")

        return '_'.join(map(str, normalized_duration))

    except Exception as e:
        raise ValueError(f"Error normalizing duration: {str(e)}")

def apply_normalization_rules(data_dict):
    for key, value in data_dict.items():
        if key == 'ДатаДокумента':
            data_dict[key] = normalize_date(value)
        elif key == 'СрокОплаты':
            data_dict[key] = normalize_duration(value)
        elif isinstance(value, dict):
            apply_normalization_rules(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    apply_normalization_rules(item)

    return data_dict

@app.route('/process_tree', methods=['POST'])
def process_tree():
    try:
        data = request.get_data().decode('utf-8')
        if request.content_type == 'application/json':
            tree_dict = convert_json_to_dict(json.loads(data))
        elif request.content_type == 'application/xml':
            xml_root = ET.fromstring(data)
            tree_dict = xml_to_dict(xml_root)
        else:
            return jsonify({"error": "Unsupported Content-Type"}), 400
        
        normalized_tree = apply_normalization_rules(tree_dict)

        return jsonify(normalized_tree)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
