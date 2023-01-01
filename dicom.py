# dicom.py
# Parsing DICOM medical imaging files.

from typing import List
import xml.etree.ElementTree as ET
import io


# Invalid DICOM file exception.
class InvalidDICOMFileException(Exception):

    """The standard exception for invalid DICOM files."""


# DICOM undefined length.
UNDEFINED_LENGTH = 0xffffffff

# List of value representations that require an explicit 16-bit value length field (see DICOM PS3.5 2022d 7.1.2)
VR_EXPLICIT_16BIT_VLF = ['AE', 'AS', 'AT', 'CS', 'DA', 'DS', 'DT', 'FL', 'FD', 'IS', 'LO', 'LT', 'PN', 'SH', 'SL', 'SS', 'ST', 'TM', 'UI', 'UL', 'US']


# Data element tag.
class ElementTag:

    """A DICOM data element tag object."""

    def __init__(self, group: int, elem: int):

        """Create a new element tag."""

        self.group = group
        self.elem = elem

    def __eq__(self, other) -> bool:
        
        """Check equality between element tags."""

        if not isinstance(other, ElementTag):
            return False

        if (self.group != other.group) or (self.elem != other.elem):
            return False
        
        return True

    def __repr__(self) -> str:

        """Return a string representation of the tag."""

        return f'Tag({hex(self.group)}, {hex(self.elem)})'

    def __str__(self) -> str:

        """Return a string representation of the tag."""

        return self.__repr__()


# DICOM file object.
class DICOM:

    """A DICOM file."""

    def __init__(self, path: str, preamble: bytes, dataset: List):
    
        """Create the DICOM file object."""

        self.path = path
        self.preamble = preamble
        self.dataset = dataset

    def find_elements_by_tag(self, tag: ElementTag) -> List:

        """Find elements by element tag."""

        elements = []
        for item in self.dataset:
            if item.tag == tag:
                elements.append(item)
        return elements

    def __repr__(self) -> str:

        """Return a string representation of the DICOM file."""

        return f'DICOM({self.path}, size={len(self.dataset)})'

    def __str__(self) -> str:

        """Return a string representation of the DICOM file."""

        return self.__repr__()


# Data element class.
class DataElement:

    """A DICOM data element object within a dataset."""

    def __init__(self, tag: ElementTag, val_repr: str, val_length: int, val_data: bytes, children: List):

        """Create a new data element."""

        self.tag = tag
        self.val_repr = val_repr
        self.val_length = val_length if val_length != UNDEFINED_LENGTH else None
        self.val_data = val_data
        self.children = children

    def is_length_undefined(self) -> bool:

        """Determine if the length of the element is undefined."""

        if self.val_length == None:
            return True
        return False

    def add_children(self, children: List):

        """Append a child to the element."""

        self.children += children

    def __repr__(self) -> str:

        """Return a string representation of the data element."""

        return f'DataElement({self.tag}, vr={self.val_repr}, vl={self.val_length if self.val_length else "UNDEFINED"}, children={self.children})'

    def __str__(self) -> str:

        """Return a string representation of the data element."""

        return self.__repr__()

# Item element.
class ItemDataElement(DataElement):

    """An item data element, a special type of data element."""

    def __init__(self, val_length: int, val_data: bytes, children: List):

        """Create a new data element."""

        self.tag = ElementTag(0xfffe, 0xe000)
        self.val_repr = None
        self.val_length = val_length if val_length != UNDEFINED_LENGTH else None
        self.val_data = val_data
        self.children = children

    def __repr__(self) -> str:

        """Return a string representation of the data element."""

        return f'ItemDataElement(vl={self.val_length if self.val_length else "UNDEFINED"}, children={self.children})'

    def __str__(self) -> str:

        """Return a string representation of the data element."""

        return self.__repr__()

# Item delimitation element.
class ItemDelimitationElement(DataElement):

    """An item delimitation element, a special type of data element."""

    def __init__(self, val_length: int, val_data: bytes, children: List):

        """Create a new data element."""

        self.tag = ElementTag(0xfffe, 0xe00d)
        self.val_repr = None
        self.val_length = val_length if val_length != UNDEFINED_LENGTH else None
        self.val_data = val_data
        self.children = children

    def __repr__(self) -> str:

        """Return a string representation of the data element."""

        return f'ItemDelimitationElement(vl={self.val_length if self.val_length else "UNDEFINED"}, children={self.children})'

    def __str__(self) -> str:

        """Return a string representation of the data element."""

        return self.__repr__()

# Sequence delimitation element.
class SequenceDelimitationElement(DataElement):

    """An sequence delimitation element, a special type of data element."""

    def __init__(self, val_length: int, val_data: bytes, children: List):

        """Create a new data element."""

        self.tag = ElementTag(0xfffe, 0xe0dd)
        self.val_repr = None
        self.val_length = val_length if val_length != UNDEFINED_LENGTH else None
        self.val_data = val_data
        self.children = children

    def __repr__(self) -> str:

        """Return a string representation of the data element."""

        return f'SequenceDelimitationElement(vl={self.val_length if self.val_length else "UNDEFINED"}, children={self.children})'

    def __str__(self) -> str:

        """Return a string representation of the data element."""

        return self.__repr__()


# Load a DICOM file.
def load(path: str) -> DICOM:

    """Load a DICOM file by path."""

    # Open the file.
    with open(path, 'rb') as f:
        # Read the preamble and magic data.
        preamble = f.read(128)
        magic = f.read(4)
        if magic != b'DICM':
            raise InvalidDICOMFileException("invalid magic header")

        # Start reading the dataset.
        dataset = read_dataset(f)
    
    return DICOM(path, preamble, dataset)

# Read the DICOM dataset from an open file.
def read_dataset(f: io.BufferedIOBase) -> List:

    """Recursively read the DICOM dataset, stopping when we reach a delimitation or we run out of data."""

    dataset = []
    while True:
        # Read a single dataset item.
        item = read_dataset_item(f)

        # Append the item, if it is 
        if item is not None:
            dataset.append(item)
        else:
            break

        # If the item is of undefined length, recursively read.
        if item.is_length_undefined():
            item.add_children(read_dataset(f))

        # If the item is a deliminator, stop reading.
        if isinstance(item, SequenceDelimitationElement) or isinstance(item, ItemDelimitationElement):
            break

    return dataset

# Read a single DICOM dataset item from an open file.
def read_dataset_item(f: io.BufferedIOBase) -> DataElement:
    
    """Read a single DICOM dataset item from an open file. Returns None if there is no more data."""

    # Read the the data element tag.
    tag_data = f.read(4)
    if not tag_data:
        return None

    group_num, element_num = int.from_bytes(tag_data[:2], byteorder='little'), int.from_bytes(tag_data[2:4], byteorder='little')

    # Check for special sequence elements.
    if group_num == 0xfffe and element_num == 0xe000:
        # Item element.
        length = int.from_bytes(f.read(4), byteorder='little')
        if length != UNDEFINED_LENGTH:
            # Non-undefined length, read the data.
            return ItemDataElement(length, f.read(length), [])
        else:
            # Undefined length.
            return ItemDataElement(length, None, [])
    elif group_num == 0xfffe and element_num == 0xe00d:
        # Item delimitation element.
        length = int.from_bytes(f.read(4), byteorder='little')
        if length != UNDEFINED_LENGTH:
            # Non-undefined length, read the data.
            return ItemDelimitationElement(length, f.read(length), [])
        else:
            # Undefined length.
            return ItemDelimitationElement(length, None, [])
    elif group_num == 0xfffe and element_num == 0xe0dd:
        # Sequence delimitation element.
        length = int.from_bytes(f.read(4), byteorder='little')
        if length != UNDEFINED_LENGTH:
            # Non-undefined length, read the data.
            return SequenceDelimitationElement(length, f.read(length), [])
        else:
            # Undefined length.
            return SequenceDelimitationElement(length, None, [])

    # Read the value representation type.
    value_repr = str(f.read(2), encoding='utf-8')
    
    # Read the length.
    length = 0
    if value_repr in VR_EXPLICIT_16BIT_VLF:
        # 16-bit length value.
        length = int.from_bytes(f.read(2), byteorder='little')
    else:
        # 32-bit length value. Read the two null bytes first.
        f.read(2)
        length = int.from_bytes(f.read(4), byteorder='little')

    # Check for an undefined length.
    if length == UNDEFINED_LENGTH:
        return DataElement(ElementTag(group_num, element_num), value_repr, length, None, [])
    else:
        # Read the data.
        data = f.read(length)
        return DataElement(ElementTag(group_num, element_num), value_repr, length, data, [])


# Dump a DICOM file to XML.
def dump_xml(dicom: DICOM, path: str):

    """Dump a DICOM file to XML."""

    # Create the XML element.
    root = ET.Element("DICOM")
    root.text = str(dicom.preamble)

    # Add the dataset elements.
    for item in dicom.dataset:
        dump_element_xml_tree(item, root)

    # Write the XML file.
    with open(path, 'wb') as f:
        f.write(ET.tostring(root))
    
# Dump a data element recursively as an XML tree.
def dump_element_xml_tree(item: DataElement, parent: ET.Element):

    """Dump a data element recursively as an XML element."""

    # Create the sub element.
    elem = ET.SubElement(parent, item.__class__.__name__)
    elem.set('group', hex(item.tag.group))
    elem.set('elem', hex(item.tag.elem))
    elem.set('vr', str(item.val_repr))
    elem.set('vl', str(item.val_length))
    
    # Add the data.
    elem.text = str(item.val_data)
    
    # Add the children.
    for child in item.children:
        dump_element_xml_tree(child, elem)
