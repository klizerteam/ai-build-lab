"""
tool_registry.py  <-- YOU write the missing parts of this file during the workshop.

THE REGISTRATION: connects each schema (tool_schemas.py) to its function
(tools.py). agent.py only ever reads the two lists below:

    TOOLS           the schemas sent to the model: its "menu" of tools
    TOOL_FUNCTIONS  tool name -> Python function. This is the ALLOWLIST:
                    when the model asks for a tool, agent.py looks up the
                    name here. A name that isn't here is refused.

Every tool has three parts, each in its own file:

    1. tools.py          the FUNCTION      what our backend runs
    2. tool_schemas.py   the SCHEMA        what the model reads
    3. tool_registry.py  the REGISTRATION  connects 1 and 2          <- this file

Registering a tool switches it ON. Finish its function and schema FIRST
(python check.py <step> tells you when they're done), then register it.
"""
from app import tool_schemas, tools

TOOLS = []            # tool schemas the model can see
TOOL_FUNCTIONS = {}   # tool name -> Python function (the allowlist)


# ----------------------------------------------------------------------
# STEP 3: search_products
# TASK 3H: switch the tool on: delete the "# " at the start of both lines.
# ----------------------------------------------------------------------

# TOOLS.append(tool_schemas.SEARCH_PRODUCTS_SCHEMA)
# TOOL_FUNCTIONS["search_products"] = tools.search_products


# ----------------------------------------------------------------------
# STEP 4: check_order
# TASK 4F: write the two lines that register check_order.
# ----------------------------------------------------------------------



# ----------------------------------------------------------------------
# STEP 5: calculate_discount
# TASK 5F: write the two lines that register calculate_discount.
# ----------------------------------------------------------------------

