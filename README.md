# harvester

An easy-to-use Web Scraping tool.

### Model

The Model class is responsible to bring together the information contained in a URL, which may be comprised by the data
included in the content, even if this data is actually included in the content of a refered url.

TBD Initalization parameters

#### inner Meta class

The inner Meta class has information about how to preprocess the content returnde by the server BEFORE the actual
content gathering.

TBD drop_before and drop_after

### Field

The Field class represents piece of information obtained from the total set of information returned by the server.
There are different subclasses of Field, each for a particular case.

TBD Initialization parameters
TBD Field Subclasses

# Note

English included both in this document and the code can be devastating for the brain of an average human being. Even so
we, the poor developers, are working hard to write as correctly as possible and learn along the way. The documentation
will be updated as we improve our language proficency as well as we receive critical / suggestions for this.