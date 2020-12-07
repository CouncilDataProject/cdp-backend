# Event Ingestion Model

We try to make CDP infrastructure as easy as possible to set while also scaling to
support as much specific data as can be given and processed.

To this end, our event data ingestion model can be seen below where in one example, the
bare minimum is provided to the `Event` object, while in another, details about minutes
items that were discussed during the event are attached.

The more data provided to each `Event` object, the more data displayed and queryable
from CDP services.

For more information on each field available, please see the
[object definition documentation](./cdp_backend.pipeline.html#module-cdp_backend.pipeline.ingestion_models).

## Minimal Event Data

```python
{'body': {'name': 'Full Council', 'is_active': True},
 'sessions': [{'session_datetime': datetime.datetime(2020, 12, 7, 6, 31, 39, 600569),
               'video_uri': 'https://youtu.be/dQw4w9WgXcQ'}]}
```

## Expanded Event Data with Event Minutes Items

```python
{'body': {'name': 'Full Council', 'is_active': True},
 'sessions': [{'session_datetime': datetime.datetime(2020, 12, 7, 6, 31, 39, 600574),
               'video_uri': 'https://youtu.be/dQw4w9WgXcQ'}],
 'event_minutes_items': [{'minutes_item': {'name': 'Inf 1656'}},
                         {'minutes_item': {'name': 'CB 119858'},
                          'matter': {'name': 'CB 119858',
                                     'matter_type': 'Council Bill',
                                     'title': 'AN ORDINANCE relating to the '
                                              'financing of the West Seattle '
                                              'Bridge',
                                     'sponsors': [{'name': 'M. Lorena González',
                                                   'is_active': True,
                                                   'seat': {'name': 'Position '
                                                                    '9'},
                                                   'roles': [{'title': 'Council '
                                                                       'President'},
                                                             {'title': 'Chair',
                                                              'body': {'name': 'Governance '
                                                                               'and '
                                                                               'Education',
                                                                       'is_active': True}}]},
                                                  {'name': 'Teresa Mosqueda',
                                                   'is_active': True,
                                                   'seat': {'name': 'Position '
                                                                    '8'},
                                                   'roles': [{'title': 'Chair',
                                                              'body': {'name': 'Finance '
                                                                               'and '
                                                                               'Housing',
                                                                       'is_active': True}},
                                                             {'title': 'Vice '
                                                                       'Chair',
                                                              'body': {'name': 'Governance '
                                                                               'and '
                                                                               'Education',
                                                                       'is_active': True}}]}]},
                          'supporting_files': [{'name': 'Amendment 3',
                                                'uri': 'http://legistar2.granicus.com/seattle/attachments/789a0c9f-dd9c-401b-aaf5-6c67c2a897b0.pdf'}],
                          'decision': 'Passed',
                          'votes': [{'person': {'name': 'M. Lorena González',
                                                'is_active': True,
                                                'seat': {'name': 'Position 9'},
                                                'roles': [{'title': 'Council '
                                                                    'President'},
                                                          {'title': 'Chair',
                                                           'body': {'name': 'Governance '
                                                                            'and '
                                                                            'Education',
                                                                    'is_active': True}}]},
                                     'decision': 'Approve'},
                                    {'person': {'name': 'Teresa Mosqueda',
                                                'is_active': True,
                                                'seat': {'name': 'Position 8'},
                                                'roles': [{'title': 'Chair',
                                                           'body': {'name': 'Finance '
                                                                            'and '
                                                                            'Housing',
                                                                    'is_active': True}},
                                                          {'title': 'Vice '
                                                                    'Chair',
                                                           'body': {'name': 'Governance '
                                                                            'and '
                                                                            'Education',
                                                                    'is_active': True}}]},
                                     'decision': 'Approve'},
                                    {'person': {'name': 'Andrew Lewis',
                                                'is_active': True,
                                                'seat': {'name': 'District 7'},
                                                'roles': [{'title': 'Vice '
                                                                    'Chair',
                                                           'body': {'name': 'Community '
                                                                            'Economic '
                                                                            'Development',
                                                                    'is_active': True}}]},
                                     'decision': 'Approve'},
                                    {'person': {'name': 'Alex Pedersen',
                                                'is_active': True,
                                                'seat': {'name': 'District 4'},
                                                'roles': [{'title': 'Chair',
                                                           'body': {'name': 'Transportation '
                                                                            'and '
                                                                            'Utilities',
                                                                    'is_active': True}}]},
                                     'decision': 'Reject'}]}]}
```