"""Probe: give the OWL the rdfs:domain WebVOWL needs, from what is already there.

gen-owl writes a slot's domain as an owl:Restriction inside the declaring class
and never as rdfs:domain. VOWL draws a property as an edge only when it carries
both a domain and a range, so all 18 object properties render out of one generic
node and the only class-to-class edges left are the 7 subClassOf links.

Nothing is invented. Every (class, property) pair is read straight off the
restrictions already in the file, and it was measured first: 49 pairs, one per
property, none ambiguous. A serialisation change, not a modelling one.

Throwaway probe. If it should live, it enters through NEXT.md.
"""

import sys

import rdflib
from rdflib.namespace import RDF, RDFS, OWL

src, dst = sys.argv[1], sys.argv[2]

g = rdflib.Graph()
g.parse(src, format="turtle")

before = len(list(g.triples((None, RDFS.domain, None))))

pairs = set()
for cls, restriction in g.subject_objects(RDFS.subClassOf):
    if (restriction, RDF.type, OWL.Restriction) not in g:
        continue
    if not isinstance(cls, rdflib.URIRef):
        continue
    for prop in g.objects(restriction, OWL.onProperty):
        pairs.add((prop, cls))

for prop, cls in sorted(pairs):
    g.add((prop, RDFS.domain, cls))

g.serialize(destination=dst, format="turtle")

obj = set(g.subjects(RDF.type, OWL.ObjectProperty))
both = {p for p in obj
        if list(g.objects(p, RDFS.domain)) and list(g.objects(p, RDFS.range))}
multi = {p for p, _ in pairs if len(set(g.objects(p, RDFS.domain))) > 1}

print("rdfs:domain before        ", before)
print("rdfs:domain after         ", len(pairs))
print("object properties         ", len(obj))
print("  with domain AND range   ", len(both), "  <- edges VOWL will now draw")
print("properties with >1 domain ", len(multi), "  <- must be 0")
print("triples                   ", len(g))
