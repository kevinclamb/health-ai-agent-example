import keys
import os
from configparser import Error

from openai import OpenAI

from fhir.resources.diagnosticreport import DiagnosticReport
from fhir.resources.observation import Observation

from particle_health import ParticleHealthClient

import json

client = OpenAI(api_key=os.getenv('OPEN_AI_KEY'))
model = "gpt-4o-mini"

def convert_image_to_hl7_fhir_json(client, model, base64_image, use_cache=True):
    if use_cache is False:
        # Analyze the image and attempt conversion into HL7 FHIR Lab format
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Convert to hl7 FHIR laboratory format. Separate JSON for HL7 FHIR Laboratory Diagnostic Report and Observation",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ],
                }
            ],
        )

        print(response.choices[0])

        # Extracting the content attribute from the response object
        message_content = response.choices[0].message.content

        # Splitting the content to separate JSON blocks
        json_blocks = message_content.split("```json")

        # Parsing the JSON blocks
        parsed_jsons = []
        for block in json_blocks:
            block = block.strip().strip("```").strip()
            if block:
                try:
                    parsed_json = json.loads(block)
                    parsed_jsons.append(parsed_json)
                except json.JSONDecodeError:
                    pass  # Ignore non-JSON blocks

        return json_blocks

    else:
        diagnostic_report = """{
          "resourceType": "DiagnosticReport",
          "id": "staphylococcus-aureus-culture-2015",
          "status": "final",
          "category": {
            "coding": [
              {
                "system": "http://hl7.org/fhir/ValueSet/diagnostic-service-sections",
                "code": "LAB",
                "display": "Laboratory"
              }
            ]
          },
          "code": {
            "coding": [
              {
                "system": "http://loinc.org",
                "code": "600-7",
                "display": "Bacterial culture"
              }
            ],
            "text": "Staphylococcus aureus Culture"
          },
          "subject": {
            "reference": "Patient/example",
            "display": "Example Patient"
          },
          "effectiveDateTime": "2015-01-12T00:00:00Z",
          "issued": "2015-01-12T14:00:00Z",
          "performer": [
            {
              "reference": "Organization/lab",
              "display": "Example Clinical Laboratory"
            }
          ],
          "specimen": [
            {
              "reference": "Specimen/blood-culture",
              "display": "Blood culture (aerobic bottle)"
            }
          ],
          "result": [
            {
              "reference": "Observation/staphylococcus-aureus-susceptibility"
            }
          ]
        }
        """
        observation_resources = """{
          "resourceType": "Observation",
          "id": "staphylococcus-aureus-susceptibility",
          "status": "final",
          "category": [
            {
              "coding": [
                {
                  "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                  "code": "laboratory",
                  "display": "Laboratory"
                }
              ]
            }
          ],
          "code": {
            "coding": [
              {
                "system": "http://loinc.org",
                "code": "18834-2",
                "display": "Antibiotic susceptibility"
              }
            ],
            "text": "Staphylococcus aureus Susceptibility"
          },
          "subject": {
            "reference": "Patient/example"
          },
          "effectiveDateTime": "2015-01-12T00:00:00Z",
          "valueCodeableConcept": {
            "text": "Gram-positive cocci in clusters"
          },
          "component": [
            {
              "code": {
                "text": "Clindamycin"
              },
              "valueCodeableConcept": {
                "coding": [
                  {
                    "system": "http://snomed.info/sct",
                    "code": "40729002",
                    "display": "Resistant"
                  }
                ]
              }
            },
            {
              "code": {
                "text": "Daptomycin"
              },
              "valueCodeableConcept": {
                "coding": [
                  {
                    "system": "http://snomed.info/sct",
                    "code": "111524002",
                    "display": "Susceptible"
                  }
                ]
              }
            },
            {
              "code": {
                "text": "Vancomycin"
              },
              "valueCodeableConcept": {
                "coding": [
                  {
                    "system": "http://snomed.info/sct",
                    "code": "111524002",
                    "display": "Susceptible"
                  }
                ]
              }
            },
            {
              "code": {
                "text": "Erythromycin"
              },
              "valueCodeableConcept": {
                "coding": [
                  {
                    "system": "http://snomed.info/sct",
                    "code": "40729002",
                    "display": "Resistant"
                  }
                ]
              }
            }
          ]
        }
        """

        return json.dumps([diagnostic_report, observation_resources])

def validate_hl7_fhir_json(fhir_json):
    """
    Validates if the provided JSON is a valid FHIR DiagnosticReport or Observation resource.
    If valid, returns a success message and True. If invalid, returns an error message and False.

    :param fhir_json: dict, the JSON to validate
    :return: tuple (str, bool), validation result message and True/False indicating validity
    """
    fhir_json = json.loads(fhir_json)
    # Check if the JSON contains the 'resourceType' key
    resource_type = fhir_json.get('resourceType')
    if not resource_type:
        return "Error: 'resourceType' key is missing in the provided JSON.", False

    if resource_type == 'Observation':
        # Validate Observation
        try:
            Observation(**fhir_json)  # Validate the Observation JSON
            return "Observation JSON is valid!", True
        except Exception as e:
            return f"Observation JSON validation failed! Error: {e}", False

    elif resource_type == 'DiagnosticReport':
        # Validate DiagnosticReport
        try:
            DiagnosticReport(**fhir_json)  # Validate the DiagnosticReport JSON
            return "DiagnosticReport JSON is valid!", True
        except Exception as e:
            return f"DiagnosticReport JSON validation failed! Error: {e}", False

    else:
        # Unsupported resource type
        return f"Error: Unsupported resource type '{resource_type}'. Only 'Observation' and 'DiagnosticReport' are supported.", False

particle_client = ParticleHealthClient(os.getenv("PARTICLE_HEALTH_CLIENT_ID"),
                              os.getenv("PARTICLE_HEALTH_SECRET_KEY"))

if particle_client.authenticate():
    # Example patient data
    patient_data = {
        "address_city": "Harwich",
        "address_lines": ["710 Batz Estate"],
        "address_state": "MA",
        "date_of_birth": "1995-09-05",
        "email": "Grant@doe.com",
        "family_name": "Bogisich",
        "gender": "Male",
        "given_name": "Grant",
        "postal_code": "02645",
        "ssn": "123-45-6789",
        "telephone": "1-234-567-8910",
    }
    query_response = particle_client.create_query(patient_data)
    if query_response:
        query_id = query_response["id"]
        file_id = query_response["files"][0]["id"]
        lab_image = particle_client.get_image(query_id, file_id)

# Retrieve JSON from the visual model
hl7_fhir_json = convert_image_to_hl7_fhir_json(client, model, lab_image, use_cache=True)

# Register the tool with ChatGPT
tool_registry = {
    "validate_hl7_fhir_json": validate_hl7_fhir_json,
}

functions = [
    {"name": "validate_hl7_fhir_json",
        "description": "Validate HL& FHIR JSON. Returns a message a message describing the validity of the provided JSON (str) and a True / False if it is valid or not (bool)",
        "parameters": {
            "type": "object",
            "properties": {
                "fhir_json": {"type": "string"}
            },
            "required": ["fhir_json"],
            "additionalProperties": False
        },
    }
]

messages = [
    {
        "role": "user",
        "content": (
            "Convert to HL7 FHIR laboratory format. Separate JSON for HL7 FHIR "
            "Laboratory DiagnosticReport and Observation.\n"
            "Here is my base64 image data:\n"
            f"{lab_image}"
        )
    },
    {
        "role": "assistant",
        "content": hl7_fhir_json
    },
    {
        "role": "user",
        "content": "Is the JSON provided valid HL7 FHIR JSON?"
    }
]

response = client.chat.completions.create(
    model=model,
    messages=messages,
    functions=functions,
)

print(response.choices[0])

messages.append(response.choices[0].message)

if response.choices[0].finish_reason == 'function_call':
    function_call = response.choices[0].message.function_call

    # Use attribute access instead of subscripting:
    function_name = function_call.name
    function_args_json = function_call.arguments  # A JSON string

    # Deserialize the arguments
    function_args = json.loads(function_args_json)

    # Call the corresponding Python function from your tool registry
    if function_name in tool_registry:
        result = tool_registry[function_name](**function_args)
        print("Tool returned:", result)
        # Append the result as a new assistant message
        messages.append({
            "role": "assistant",
            "function_call": {
                "name": function_name,
                "arguments": function_args
            }
        })
        # Append the function result as a message
        messages.append({
            "role": "assistant",
            "content": result[0] if isinstance(result, tuple) else result
        })
    else:
        result = ""
        print(f"No Python tool found for function name: {function_name}")

# Send back the information from the function. the LLM will then attempt to alter the JSON accordingly
completion_2 = client.chat.completions.create(
    model=model,
    messages=messages,
    functions=functions,
)

print(response.choices[0])

diagnostic_report2 = """{
    "resourceType": "DiagnosticReport",
    "id": "staphylococcus-aureus-culture-2015",
    "status": "final",
    "category": [
        {
            "coding": [
                {
                    "system": "http://hl7.org/fhir/ValueSet/diagnostic-service-sections",
                    "code": "LAB",
                    "display": "Laboratory"
                }
            ]
        }
    ],
    "code": {
        "coding": [
            {
                "system": "http://loinc.org",
                "code": "600-7",
                "display": "Bacterial culture"
            }
        ],
        "text": "Staphylococcus aureus Culture"
    },
    "subject": {
        "reference": "Patient/example",
        "display": "Example Patient"
    },
    "effectiveDateTime": "2015-01-12T00:00:00Z",
    "issued": "2015-01-12T14:00:00Z",
    "performer": [
        {
            "reference": "Organization/lab",
            "display": "Example Clinical Laboratory"
        }
    ],
    "specimen": [
        {
            "reference": "Specimen/blood-culture",
            "display": "Blood culture (aerobic bottle)"
        }
    ],
    "result": [
        {
            "reference": "Observation/staphylococcus-aureus-susceptibility"
        }
    ]
}
"""
