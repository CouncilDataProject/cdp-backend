# CDP Database Schema

While CDP utilizes a
[NoSQL Document Store](https://en.wikipedia.org/wiki/Document-oriented_database)
called [Cloud Firestore](https://firebase.google.com/docs/firestore), it is still
useful to view the database schema as a UML diagram.

![cdp-database-schema](./_static/cdp_database_diagram.jpg)

### Notes
* `*` denotes that the field is required

### Implementation
For more details on each document model see
[our API docs](./cdp_backend.database.html#module-cdp_backend.database.models)
