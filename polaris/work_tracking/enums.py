# -*- coding: utf-8 -*-
from enum import Enum


#  Copyright (c) Exathink, LLC  2016-2023.
#  All rights reserved
#

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar
class CustomTagMappingType(Enum):
    # this applies the tag if the path selector returns a non-null-value
    path_selector = 'path-selector'

    # this applies the tag if the path selector returns the value specified
    path_selector_value_equals = 'path-selector-value'

    # this applies the tag if the path selector returns one of the values specified
    path_selector_value_in = 'path-selector-value-in'

    # this applies the tag if the path selector returns the boolean value true
    path_selector_true = 'path-selector-true'

    # this applies the tag if the path selector returns the boolean value false
    path_selector_false = 'path-selector-false'

    custom_field_populated = 'custom-field-populated'
