"""
tool_schemas.py  <-- YOU write the missing parts of this file during the workshop.

THE SCHEMAS: a description of each tool, written for the model. This is the
ONLY part of a tool the model ever sees. It tells the model:

    name         what the tool is called
    description  WHEN to use it (the model decides based on this text)
    parameters   which inputs to send, and in what format

Every tool has three parts, each in its own file:

    1. tools.py          the FUNCTION      what our backend runs
    2. tool_schemas.py   the SCHEMA        what the model reads      <- this file
    3. tool_registry.py  the REGISTRATION  connects 1 and 2

HOW IT WORKS
Replace each  ...  and write the parts marked  TASK 3E, TASK 3F, ...
Search for "TASK 3" (then "TASK 4", "TASK 5").
"""


# ----------------------------------------------------------------------
# STEP 3: search_products
# ----------------------------------------------------------------------

SEARCH_PRODUCTS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_products",
        "description": ...,  # TASK 3E: WHEN should the model use this tool?
        "parameters": {
            "type": "object",
            "properties": {
                # The "query" input (written for you, as an example):
                "query": {
                    "type": "string",
                    "description": (
                        "1-3 product keywords, e.g. 'wireless' or 'gaming'. "
                        "Do not include prices or words like 'cheap' or 'best'."
                    ),
                },
                # TASK 3F: the "category" input.
                # TASK 3G: the "max_price" input.
            },
        },
    },
}


# ----------------------------------------------------------------------
# STEP 4: check_order
# ----------------------------------------------------------------------

CHECK_ORDER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "check_order",
        "description": ...,  # TASK 4D: WHEN should the model use this tool?
        "parameters": ...,   # TASK 4E: the inputs (see SEARCH_PRODUCTS_SCHEMA)
    },
}


# ----------------------------------------------------------------------
# STEP 5: calculate_discount
# ----------------------------------------------------------------------

CALCULATE_DISCOUNT_SCHEMA = ...  # TASK 5E: the whole schema
