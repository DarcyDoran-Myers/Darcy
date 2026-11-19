"""Classify FNAI OWNER strings into public / private / nonprofit / tribal."""
import re
RULES = [
    ('tribal',    r'Indian Tribe|Tribe of|Seminole Tribe|Miccosukee'),
    ('public',    r'Trustees of the Internal Improvement'),
    ('private',   r'Power and Light|Progress Energy|LLC|L\.L\.C|Company|Corporation|corporation|Partnership|Dairy|Private Individual'),
    ('nonprofit', r'Conservancy|Land Trust|Conservation Trust|Wetlands America Trust|Audubon|Foundation|Society|Private Organization|Institute|'
                  r'Nature Center|Gardens|Museum|Expeditions|Research, Inc|Education Inc|Conservation Fund|Conservation Florida|Boy Scouts|Church|Nature Conservancy'),
    ('public',    r'Water Management District|^US |^U\.S\.|United State|National Aeronautics|^FL |Florida|County|City of|Town of|Village of|'
                  r'University|School|Authority|District|JEA|State|Department|Commission|Port\b|Federal'),
]
RULES = [(c, re.compile(p)) for c, p in RULES]
def owner_class(o):
    o = (o or '').strip()
    for c, rx in RULES:
        if rx.search(o): return c
    return 'private'
