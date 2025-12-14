import json
import logging
import httpx
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """
Analyze this screenshot of a PowerWorld Simulator buses dialog or grid view.
Extract all visible bus information into this JSON format:

{
  "buses": [
    {
      "number": <int>,
      "name": "<string>",
      "voltage_kv": <float>,
      "area": "<string>",
      "zone": "<string or null>",
      "type": "<string or null>",
      "mw_load": <float or null>,
      "mvar_load": <float or null>
    }
  ]
}

IMPORTANT:
- Only include buses that are clearly visible in the screenshot
- If a field is not visible or readable, use null
- The areas should be "Ativ Island" or "West Side County" if visible
- Bus types might include "Slack", "PV", "PQ", etc.
- Extract numbers accurately from the table/dialog

Return ONLY the JSON object, no additional text.
"""


async def extract_bus_data(screenshot_base64: str, api_key: str) -> Dict[str, Any]:
    """
    Send screenshot to Anthropic Claude to extract bus data.

    Args:
        screenshot_base64: Base64 encoded image data URL (data:image/png;base64,...)
        api_key: Anthropic API key

    Returns:
        Dictionary with extracted bus data
    """
    logger.info("Sending screenshot to Anthropic for analysis...")

    # Handle both raw base64 and data URL format
    if screenshot_base64.startswith("data:"):
        # Extract base64 part from data URL
        # Format: data:image/png;base64,<base64_data>
        parts = screenshot_base64.split(",", 1)
        if len(parts) == 2:
            image_data = parts[1]
            media_type = "image/png"
            if "jpeg" in parts[0]:
                media_type = "image/jpeg"
        else:
            image_data = screenshot_base64
            media_type = "image/png"
    else:
        image_data = screenshot_base64
        media_type = "image/png"

    # Prepare the request for Anthropic API
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": EXTRACTION_PROMPT,
                    },
                ],
            }
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

            # Extract the text content from response
            content = result.get("content", [])
            if content and len(content) > 0:
                text_response = content[0].get("text", "")

                # Parse the JSON from the response
                # Try to find JSON in the response
                try:
                    # Try direct parse first
                    bus_data = json.loads(text_response)
                    logger.info(f"Successfully extracted bus data: {len(bus_data.get('buses', []))} buses")
                    return bus_data
                except json.JSONDecodeError:
                    # Try to extract JSON from markdown code blocks
                    import re
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text_response, re.DOTALL)
                    if json_match:
                        bus_data = json.loads(json_match.group(1))
                        logger.info(f"Extracted bus data from code block: {len(bus_data.get('buses', []))} buses")
                        return bus_data

                    # Try to find raw JSON object
                    json_match = re.search(r'\{[^{}]*"buses"[^{}]*\[.*?\][^{}]*\}', text_response, re.DOTALL)
                    if json_match:
                        bus_data = json.loads(json_match.group(0))
                        return bus_data

                    logger.error(f"Could not parse JSON from response: {text_response[:500]}")
                    return {"buses": [], "error": "Could not parse response", "raw_response": text_response[:500]}

            logger.error("Empty response from Anthropic")
            return {"buses": [], "error": "Empty response from Anthropic"}

    except httpx.HTTPStatusError as e:
        logger.error(f"Anthropic API error: {e.response.status_code} - {e.response.text}")
        return {"buses": [], "error": f"API error: {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Error calling Anthropic API: {e}")
        return {"buses": [], "error": str(e)}


CONTINGENCY_EXTRACTION_PROMPT = """
Analyze this screenshot of PowerWorld Simulator Contingency Analysis results.
Extract all visible contingency information into this JSON format:

{
  "contingencies": [
    {
      "number": <int>,
      "name": "<string>",
      "circuit": "<string or null>",
      "status": "<string>",
      "violations": <int or null>,
      "worst_violation": "<string or null>",
      "worst_percent": <float or null>
    }
  ],
  "summary": {
    "total_contingencies": <int>,
    "passed": <int>,
    "failed": <int>
  }
}

IMPORTANT:
- Only include contingencies that are clearly visible in the screenshot
- If a field is not visible or readable, use null
- Status might be "Converged", "Diverged", "Passed", "Failed", etc.
- Extract all row data accurately from the results table
- Count passed/failed for the summary

Return ONLY the JSON object, no additional text.
"""


async def extract_contingency_data(screenshot_base64: str, api_key: str) -> Dict[str, Any]:
    """
    Send screenshot to Anthropic Claude to extract contingency analysis data.

    Args:
        screenshot_base64: Base64 encoded image data URL (data:image/png;base64,...)
        api_key: Anthropic API key

    Returns:
        Dictionary with extracted contingency data
    """
    logger.info("Sending contingency screenshot to Anthropic for analysis...")

    # Handle both raw base64 and data URL format
    if screenshot_base64.startswith("data:"):
        parts = screenshot_base64.split(",", 1)
        if len(parts) == 2:
            image_data = parts[1]
            media_type = "image/png"
            if "jpeg" in parts[0]:
                media_type = "image/jpeg"
        else:
            image_data = screenshot_base64
            media_type = "image/png"
    else:
        image_data = screenshot_base64
        media_type = "image/png"

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": CONTINGENCY_EXTRACTION_PROMPT,
                    },
                ],
            }
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

            content = result.get("content", [])
            if content and len(content) > 0:
                text_response = content[0].get("text", "")

                try:
                    contingency_data = json.loads(text_response)
                    num_contingencies = len(contingency_data.get('contingencies', []))
                    logger.info(f"Successfully extracted contingency data: {num_contingencies} contingencies")
                    return contingency_data
                except json.JSONDecodeError:
                    import re
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text_response, re.DOTALL)
                    if json_match:
                        contingency_data = json.loads(json_match.group(1))
                        logger.info(f"Extracted contingency data from code block")
                        return contingency_data

                    json_match = re.search(r'\{[^{}]*"contingencies"[^{}]*\[.*?\][^{}]*\}', text_response, re.DOTALL)
                    if json_match:
                        contingency_data = json.loads(json_match.group(0))
                        return contingency_data

                    logger.error(f"Could not parse JSON from response: {text_response[:500]}")
                    return {"contingencies": [], "error": "Could not parse response", "raw_response": text_response[:500]}

            logger.error("Empty response from Anthropic")
            return {"contingencies": [], "error": "Empty response from Anthropic"}

    except httpx.HTTPStatusError as e:
        logger.error(f"Anthropic API error: {e.response.status_code} - {e.response.text}")
        return {"contingencies": [], "error": f"API error: {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Error calling Anthropic API: {e}")
        return {"contingencies": [], "error": str(e)}


CONTINGENCY_MULTI_EXTRACTION_PROMPT = """
You are analyzing multiple screenshots from PowerWorld Contingency Analysis.
Each image shows the Results tab for ONE contingency.

For each image, extract:
- Contingency header info (top of results): Number, Name, Circuit, XForms, Violations, Max Loading %
- Violation details table (if present): Category, Element Name, Value, Limit, Percent

Return a single JSON combining all contingencies:

{
  "contingencies": [
    {
      "number": <int>,
      "name": "<string>",
      "circuit": "<string or null>",
      "xforms": "<string or null>",
      "violations": <int>,
      "max_loading_percent": <float or null>,
      "violation_details": [
        {
          "category": "<string>",
          "element": "<string>",
          "value": <float>,
          "limit": <float>,
          "percent": <float>
        }
      ]
    }
  ],
  "summary": {
    "total_contingencies": <int>,
    "total_violations": <int>
  }
}

Process each image as one contingency. Return ONLY the JSON.
"""


async def extract_contingency_data_multi(
    screenshots: List[str],
    api_key: str
) -> Dict[str, Any]:
    """
    Send multiple screenshots to Anthropic Claude to extract contingency data.

    Args:
        screenshots: List of base64 encoded image data URLs
        api_key: Anthropic API key

    Returns:
        Dictionary with extracted contingency data from all images
    """
    logger.info(f"Sending {len(screenshots)} contingency screenshots to Anthropic...")

    # Build content array with all images
    content = []
    for screenshot in screenshots:
        # Handle both raw base64 and data URL format
        if screenshot.startswith("data:"):
            parts = screenshot.split(",", 1)
            if len(parts) == 2:
                image_data = parts[1]
                media_type = "image/png"
                if "jpeg" in parts[0]:
                    media_type = "image/jpeg"
            else:
                image_data = screenshot
                media_type = "image/png"
        else:
            image_data = screenshot
            media_type = "image/png"

        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": image_data,
            },
        })

    # Add the prompt at the end
    content.append({
        "type": "text",
        "text": CONTINGENCY_MULTI_EXTRACTION_PROMPT,
    })

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 8192,
        "messages": [{"role": "user", "content": content}],
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

            content = result.get("content", [])
            if content and len(content) > 0:
                text_response = content[0].get("text", "")

                try:
                    contingency_data = json.loads(text_response)
                    num_contingencies = len(contingency_data.get('contingencies', []))
                    logger.info(f"Successfully extracted {num_contingencies} contingencies from {len(screenshots)} images")
                    return contingency_data
                except json.JSONDecodeError:
                    import re
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text_response, re.DOTALL)
                    if json_match:
                        contingency_data = json.loads(json_match.group(1))
                        logger.info(f"Extracted contingency data from code block")
                        return contingency_data

                    json_match = re.search(r'\{.*"contingencies".*\}', text_response, re.DOTALL)
                    if json_match:
                        contingency_data = json.loads(json_match.group(0))
                        return contingency_data

                    logger.error(f"Could not parse JSON from response: {text_response[:500]}")
                    return {"contingencies": [], "error": "Could not parse response", "raw_response": text_response[:500]}

            logger.error("Empty response from Anthropic")
            return {"contingencies": [], "error": "Empty response from Anthropic"}

    except httpx.HTTPStatusError as e:
        logger.error(f"Anthropic API error: {e.response.status_code} - {e.response.text}")
        return {"contingencies": [], "error": f"API error: {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Error calling Anthropic API: {e}")
        return {"contingencies": [], "error": str(e)}


GRID_EXTRACTION_PROMPT = """
Analyze this screenshot of a PowerWorld Simulator power grid in Run Mode.
Extract information about the grid structure and power flow into this JSON format:

{
  "grid": {
    "name": "<string>",
    "status": "<string - e.g., 'Running', 'Idle'>",
    "areas": [
      {
        "name": "<string>",
        "buses": <int>,
        "generators": <int>,
        "loads": <int>
      }
    ],
    "summary": {
      "total_buses": <int>,
      "total_generators": <int>,
      "total_loads": <int>,
      "total_lines": <int>
    },
    "observations": [
      "<string - any notable observations about the grid state>"
    ]
  }
}

IMPORTANT:
- Identify the grid name if visible
- Count visible elements (buses, generators, loads, lines)
- Note the areas if visible (e.g., "Ativ Island", "West Side County")
- Add any observations about power flow, violations, or status

Return ONLY the JSON object, no additional text.
"""


async def extract_grid_data(screenshot_base64: str, api_key: str) -> Dict[str, Any]:
    """
    Send screenshot to Anthropic Claude to analyze power grid.

    Args:
        screenshot_base64: Base64 encoded image data URL (data:image/png;base64,...)
        api_key: Anthropic API key

    Returns:
        Dictionary with grid analysis data
    """
    logger.info("Sending grid screenshot to Anthropic for analysis...")

    # Handle both raw base64 and data URL format
    if screenshot_base64.startswith("data:"):
        parts = screenshot_base64.split(",", 1)
        if len(parts) == 2:
            image_data = parts[1]
            media_type = "image/png"
            if "jpeg" in parts[0]:
                media_type = "image/jpeg"
        else:
            image_data = screenshot_base64
            media_type = "image/png"
    else:
        image_data = screenshot_base64
        media_type = "image/png"

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": GRID_EXTRACTION_PROMPT,
                    },
                ],
            }
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

            content = result.get("content", [])
            if content and len(content) > 0:
                text_response = content[0].get("text", "")

                try:
                    grid_data = json.loads(text_response)
                    logger.info("Successfully extracted grid data")
                    return grid_data
                except json.JSONDecodeError:
                    import re
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text_response, re.DOTALL)
                    if json_match:
                        grid_data = json.loads(json_match.group(1))
                        logger.info("Extracted grid data from code block")
                        return grid_data

                    json_match = re.search(r'\{.*"grid".*\}', text_response, re.DOTALL)
                    if json_match:
                        grid_data = json.loads(json_match.group(0))
                        return grid_data

                    logger.error(f"Could not parse JSON from response: {text_response[:500]}")
                    return {"grid": {}, "error": "Could not parse response", "raw_response": text_response[:500]}

            logger.error("Empty response from Anthropic")
            return {"grid": {}, "error": "Empty response from Anthropic"}

    except httpx.HTTPStatusError as e:
        logger.error(f"Anthropic API error: {e.response.status_code} - {e.response.text}")
        return {"grid": {}, "error": f"API error: {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Error calling Anthropic API: {e}")
        return {"grid": {}, "error": str(e)}