"""
Working through a vector polygon driver
"""

# A: Create a polygon with control surfaces
points = list()
# Allocate
ldl 0 # Load number of points
shift 1 # multiply by 2 (number of points)
ajw -1 # stack is now at first point 
ldl 0 # x
ldl 1 # y