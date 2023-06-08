"""
Utilities for creating and working with Zinc Groups and selection.
"""

from cmlibs.utils.zinc.general import ChangeManager, HierarchicalChangeManager
from cmlibs.zinc.field import Field, FieldGroup


def group_add_group_elements(group: FieldGroup, other_group: FieldGroup, highest_dimension_only=True):
    """
    Add to group elements and/or nodes from other_group, which may be in the same or a descendent region.
    Note only objects from other_group's region are added.
    :param group: The FieldGroup to modify.
    :param other_group: FieldGroup within region tree of group's region to add contents from.
    :param highest_dimension_only: If set (default), only add elements of
    highest dimension present in other_group, otherwise add all dimensions.
    """
    region = group.getFieldmodule().getRegion()
    with HierarchicalChangeManager(region):
        other_fieldmodule = other_group.getFieldmodule()
        for dimension in range(3, -1, -1):
            if dimension > 0:
                mesh = other_fieldmodule.findMeshByDimension(dimension)
                other_mesh_group = other_group.getMeshGroup(mesh)
                if other_mesh_group.isValid() and (other_mesh_group.getSize() > 0):
                    mesh_group = group.getOrCreateMeshGroup(mesh)
                    mesh_group.addElementsConditional(other_group)
                    if highest_dimension_only:
                        return
            elif dimension == 0:
                nodeset = other_fieldmodule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
                other_nodeset_group = other_group.getNodesetGroup(nodeset)
                if other_nodeset_group.isValid() and (other_nodeset_group.getSize() > 0):
                    nodeset_group = group.getOrCreateNodesetGroup(nodeset)
                    nodeset_group.addNodesConditional(other_group)


def group_add_group_nodes(group: FieldGroup, other_group: FieldGroup, fieldDomainType):
    """
    Add to group nodes or datapoints from other_group, which may be in the same or a descendent region.
    Note only objects from other_group's region are added.
    :param group:  Zinc FieldGroup to modify.
    :param other_group:  Zinc FieldGroup to add nodes from.
    :param fieldDomainType: Field DOMAIN_TYPE_NODES or DOMAIN_TYPE_DATAPOINTS.
    """
    other_fieldmodule = other_group.getFieldmodule()
    other_nodeset = other_fieldmodule.findNodesetByFieldDomainType(fieldDomainType)
    other_nodeset_group = other_group.getNodesetGroup(other_nodeset)
    if other_nodeset_group.isValid() and (other_nodeset_group.getSize() > 0):
        region = group.getFieldmodule().getRegion()
        with HierarchicalChangeManager(region):
            nodeset_group = group.getOrCreateNodesetGroup(other_nodeset)
            nodeset_group.addNodesConditional(other_group)


def group_get_highest_dimension(group: FieldGroup):
    """
    Get highest dimension of elements or nodes in Zinc group.
    :return: Dimensions from 3-0, or -1 if empty.
    """
    fieldmodule = group.getFieldmodule()
    for dimension in range(3, 0, -1):
        mesh = fieldmodule.findMeshByDimension(dimension)
        mesh_group = group.getMeshGroup(mesh)
        if mesh_group.isValid() and (mesh_group.getSize() > 0):
            return dimension
    nodeset = fieldmodule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
    nodeset_group = group.getNodesetGroup(nodeset)
    if nodeset_group.isValid() and (nodeset_group.getSize() > 0):
        return 0
    return -1


def identifier_ranges_fix(identifier_ranges):
    '''
    Sort from lowest to highest identifier and merge adjacent and overlapping
    ranges.
    :param identifier_ranges: List of identifier ranges. Modified in situ.
    '''
    identifier_ranges.sort()
    i = 1
    while i < len(identifier_ranges):
        if identifier_ranges[i][0] <= (identifier_ranges[i - 1][1] + 1):
            if identifier_ranges[i][1] > identifier_ranges[i - 1][1]:
                identifier_ranges[i - 1][1] = identifier_ranges[i][1]
            identifier_ranges.pop(i)
        else:
            i += 1


def identifier_ranges_from_string(identifier_ranges_string):
    '''
    Parse string containing identifiers and identifier ranges.
    Function is suitable for processing manual input with whitespace, trailing non-digits.
    Ranges are sorted so strictly increasing. Overlapping ranges are merged.
    Future: migrate to use .. as separator for compatibility with EX file groups and cmgui.
    :param identifier_ranges_string: Identifier ranges as a string e.g. '1-30,55,66-70'.
    '30-1, 55,66-70s' also produces the same result.
    :return: Ordered list of identifier ranges e.g. [[1,30],[55,55],[66,70]]
    '''
    identifier_ranges = []
    for identifier_range_string in identifier_ranges_string.split(','):
        try:
            identifier_range_ends = identifier_range_string.split('-')
            # after leading whitespace, stop at first non-digit
            for e in range(len(identifier_range_ends)):
                # strip whitespace, trailing non digits
                digits = identifier_range_ends[e].strip()
                for i in range(len(digits)):
                    if not digits[i].isdigit():
                        digits = digits[:i]
                        break
                identifier_range_ends[e] = digits
            start = int(identifier_range_ends[0])
            if len(identifier_range_ends) == 1:
                stop = start
            else:
                stop = int(identifier_range_ends[1])
                # ensure range is low-high
                if stop < start:
                    start, stop = stop, start
            identifier_ranges.append([start, stop])
        except:
            pass
    identifier_ranges_fix(identifier_ranges)
    return identifier_ranges


def identifier_ranges_to_string(identifier_ranges):
    '''
    Convert ranges to a string, contracting single object ranges.
    Future: migrate to use .. as separator for compatibility with EX file groups and cmgui.
    :param identifier_ranges: Ordered list of identifier ranges e.g. [[1,30],[55,55],[66,70]]
    :return: Identifier ranges as a string e.g. '1-30,55,66-70'
    '''
    identifier_ranges_string = ''
    first = True
    for identifier_range in identifier_ranges:
        if identifier_range[0] == identifier_range[1]:
            identifier_range_string = str(identifier_range[0])
        else:
            identifier_range_string = str(identifier_range[0]) + '-' + str(identifier_range[1])
        if first:
            identifier_ranges_string = identifier_range_string
            first = False
        else:
            identifier_ranges_string += ',' + identifier_range_string
    return identifier_ranges_string


def domain_iterator_to_identifier_ranges(iterator):
    '''
    Extract sorted identifier ranges from iterator.
    Currently requires iterator to be in lowest-highest identifier order.
    Objects must support getIdentifier() method returning unique integer.
    :param iterator: A Zinc Elementiterator or Nodeiterator.
    :return: List of sorted identifier ranges [start,stop] e.g. [[1,30],[55,55],[66,70]]
    '''
    identifier_ranges = []
    obj = iterator.next()
    if obj.isValid():
        stop = start = obj.getIdentifier()
        obj = iterator.next()
        while obj.isValid():
            identifier = obj.getIdentifier()
            if identifier == (stop + 1):
                stop = identifier
            else:
                identifier_ranges.append([ start, stop ])
                stop = start = identifier
            obj = iterator.next()
        identifier_ranges.append([ start, stop ])
    return identifier_ranges


def mesh_group_add_identifier_ranges(mesh_group, identifier_ranges):
    '''
    Add elements with the supplied identifier ranges to mesh_group.
    :param mesh_group: Zinc MeshGroup to modify.
    '''
    mesh = mesh_group.getMasterMesh()
    fieldmodule = mesh.getFieldmodule()
    with ChangeManager(fieldmodule):
        for identifier_range in identifier_ranges:
            for identifier in range(identifier_range[0], identifier_range[1] + 1):
                element = mesh.findElementByIdentifier(identifier)
                mesh_group.addElement(element)


def mesh_group_to_identifier_ranges(mesh_group):
    '''
    :param mesh_group: Zinc MeshGroup.
    :return: Ordered list of element identifier ranges e.g. [[1,30],[55,55],[66,70]]
    '''
    return domain_iterator_to_identifier_ranges(mesh_group.createElementiterator())


def nodeset_group_add_identifier_ranges(nodeset_group, identifier_ranges):
    '''
    Add nodes with the supplied identifier ranges to nodeset_group.
    :param nodeset_group: Zinc NodesetGroup to modify.
    '''
    nodeset = nodeset_group.getMasterNodeset()
    fieldmodule = nodeset.getFieldmodule()
    with ChangeManager(fieldmodule):
        for identifier_range in identifier_ranges:
            for identifier in range(identifier_range[0], identifier_range[1] + 1):
                node = nodeset.findNodeByIdentifier(identifier)
                nodeset_group.addNode(node)


def nodeset_group_to_identifier_ranges(nodeset_group):
    '''
    :param nodeset_group: Zinc NodesetGroup.
    :return: Ordered list of node identifier ranges e.g. [[1,30],[55,55],[66,70]]
    '''
    return domain_iterator_to_identifier_ranges(nodeset_group.createNodeiterator())
