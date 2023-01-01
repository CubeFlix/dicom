# dicom

a library for reading DICOM (https://en.wikipedia.org/wiki/DICOM) files in python. 

## example

```
from dicom import *

file = load(r"/path/to/my/dicom/file")
print(dicom.dataset)
```