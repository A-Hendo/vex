"""Tests package for vex."""

import sys

# In modern Python, we use str for paths mostly,
# but some parts of vex might still expect bytes for shell config etc.
path_type = str
str_type = str
